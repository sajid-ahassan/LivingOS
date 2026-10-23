from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline

from app.ml.features import FEATURES


RANDOM_STATE = 42


def normalize_risk(
    raw: np.ndarray,
    p01: float,
    p99: float,
) -> np.ndarray:
    span = max(p99 - p01, 1e-12)
    return np.clip((raw - p01) / span, 0.0, 1.0)


def precision_at_k(
    labels: np.ndarray,
    risk: np.ndarray,
    k: int,
) -> float:
    if len(labels) == 0:
        return 0.0
    k = max(1, min(int(k), len(labels)))
    idx = np.argsort(-risk)[:k]
    return float(labels[idx].mean())


def choose_threshold(
    labels: np.ndarray,
    risk: np.ndarray,
) -> dict:
    """
    Select the operating threshold on VALIDATION data only.

    We maximize F1 over candidate thresholds. This is appropriate for the
    SPEDIA pilot because known attacker-origin validation windows are available.
    The chosen threshold is then frozen and evaluated once on the test split.
    """
    candidates = np.unique(
        np.concatenate(
            [
                np.linspace(0.05, 0.95, 91),
                risk,
            ]
        )
    )

    best = None

    for threshold in candidates:
        alerts = risk >= threshold

        tp = int(((labels == 1) & alerts).sum())
        fp = int(((labels == 0) & alerts).sum())
        fn = int(((labels == 1) & ~alerts).sum())

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        candidate = {
            "threshold": float(threshold),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "alerts": int(alerts.sum()),
            "true_positives": tp,
        }

        if best is None:
            best = candidate
            continue

        # Primary objective: F1.
        # Tie-break: higher recall, then fewer alerts.
        if (
            candidate["f1"] > best["f1"]
            or (
                candidate["f1"] == best["f1"]
                and candidate["recall"] > best["recall"]
            )
            or (
                candidate["f1"] == best["f1"]
                and candidate["recall"] == best["recall"]
                and candidate["alerts"] < best["alerts"]
            )
        ):
            best = candidate

    if best is None:
        raise ValueError("Could not choose a validation threshold.")

    return best


def train_and_evaluate(
    features_path: str | Path,
    model_out: str | Path,
    report_out: str | Path,
) -> dict:
    df = pd.read_csv(
        features_path,
        parse_dates=["window_start"],
    ).sort_values("window_start").reset_index(drop=True)

    if len(df) < 100:
        raise ValueError(
            "Too few user-hour windows for chronological evaluation."
        )

    unique_times = np.array(
        sorted(df["window_start"].dropna().unique())
    )

    if len(unique_times) < 10:
        raise ValueError(
            "Too few distinct time windows for train/validation/test split."
        )

    train_end = unique_times[int(len(unique_times) * 0.60)]
    valid_end = unique_times[int(len(unique_times) * 0.80)]

    train = df[df["window_start"] < train_end].copy()
    valid = df[
        (df["window_start"] >= train_end)
        & (df["window_start"] < valid_end)
    ].copy()
    test = df[df["window_start"] >= valid_end].copy()

    train_normal = train[
        train["is_known_attack"].astype(int) == 0
    ].copy()

    if train_normal.empty or valid.empty or test.empty:
        raise ValueError(
            "Chronological split produced an empty partition."
        )

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "detector",
                IsolationForest(
                    n_estimators=300,
                    max_samples=min(10_000, len(train_normal)),
                    contamination="auto",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(train_normal[FEATURES])

    valid_raw = -model.decision_function(valid[FEATURES])

    p01 = float(np.percentile(valid_raw, 1))
    p99 = float(np.percentile(valid_raw, 99))
    valid_risk = normalize_risk(valid_raw, p01, p99)

    valid_labels = valid["is_known_attack"].astype(int).to_numpy()

    threshold_selection = choose_threshold(
        valid_labels,
        valid_risk,
    )
    threshold = threshold_selection["threshold"]

    test_raw = -model.decision_function(test[FEATURES])
    test_risk = normalize_risk(test_raw, p01, p99)

    labels = test["is_known_attack"].astype(int).to_numpy()
    alerts = test_risk >= threshold

    positives = int(labels.sum())
    detected = int(((labels == 1) & alerts).sum())
    alert_count = int(alerts.sum())

    if positives > 0:
        pr_auc = float(
            average_precision_score(labels, test_risk)
        )
        recall = detected / positives
    else:
        pr_auc = None
        recall = None

    precision = (
        detected / alert_count
        if alert_count
        else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if recall is not None and (precision + recall) > 0
        else None
    )

    top_k = max(1, alert_count)

    report = {
        "dataset": "SPEDIA",
        "label_definition": (
            "Known-attack evaluation windows contain at least one "
            "event whose Agent_name begins with 'atacante_'. "
            "Agent_name is not used as a model feature."
        ),
        "rows": {
            "all_windows": int(len(df)),
            "train": int(len(train)),
            "train_normal": int(len(train_normal)),
            "validation": int(len(valid)),
            "test": int(len(test)),
        },
        "known_attack_windows": {
            "train": int(train["is_known_attack"].sum()),
            "validation": int(valid["is_known_attack"].sum()),
            "test": positives,
        },
        "threshold": threshold,
        "threshold_selection": {
            "method": "validation_f1",
            **threshold_selection,
        },
        "calibration": {
            "p01": p01,
            "p99": p99,
        },
        "metrics": {
            "pr_auc": pr_auc,
            "known_attack_recall": recall,
            "alert_precision": precision,
            "f1": f1,
            "precision_at_top_k": precision_at_k(
                labels,
                test_risk,
                top_k,
            ),
            "top_k": top_k,
            "alerts_per_thousand": float(
                alert_count / len(test) * 1000
            ),
            "alerts": alert_count,
            "known_attack_windows": positives,
            "detected_known_attack_windows": detected,
        },
    }

    bundle = {
        "model": model,
        "feature_names": FEATURES,
        "p01": p01,
        "p99": p99,
        "threshold": threshold,
        "dataset_name": "SPEDIA",
        "training_period": {
            "train_before": str(pd.Timestamp(train_end)),
            "validation_before": str(pd.Timestamp(valid_end)),
        },
        "threshold_method": "validation_f1",
        "label_definition": report["label_definition"],
        "code_version": "livingops-stage2.9-spedia-v2",
    }

    model_out = Path(model_out)
    report_out = Path(report_out)

    model_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(bundle, model_out)
    report_out.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(f"Saved model: {model_out}")
    print(f"Saved report: {report_out}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train LivingOps Isolation Forest on SPEDIA."
    )
    parser.add_argument("--features", required=True)
    parser.add_argument("--model-out", required=True)
    parser.add_argument("--report-out", required=True)
    args = parser.parse_args()

    train_and_evaluate(
        features_path=args.features,
        model_out=args.model_out,
        report_out=args.report_out,
    )


if __name__ == "__main__":
    main()
