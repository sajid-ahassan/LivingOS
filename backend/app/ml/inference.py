from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np

from app.ml.features import FEATURES


MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "isolation_forest.joblib"


@lru_cache(maxsize=1)
def load_bundle() -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Isolation Forest artifact not found: {MODEL_PATH}"
        )

    bundle = joblib.load(MODEL_PATH)

    required = {
        "model",
        "feature_names",
        "p01",
        "p99",
        "threshold",
    }
    missing = required.difference(bundle)
    if missing:
        raise ValueError(
            f"Incompatible ML artifact; missing keys: {sorted(missing)}"
        )

    if list(bundle["feature_names"]) != list(FEATURES):
        raise ValueError(
            "ML artifact feature schema does not match app.ml.features.FEATURES"
        )

    return bundle


def _normalise_risk(raw_score: float, p01: float, p99: float) -> float:
    span = max(float(p99) - float(p01), 1e-12)
    risk = (float(raw_score) - float(p01)) / span
    return float(np.clip(risk, 0.0, 1.0))


def score_feature_vector(features: dict[str, float | int]) -> dict:
    bundle = load_bundle()

    ordered = []
    for feature_name in bundle["feature_names"]:
        if feature_name not in features:
            raise ValueError(f"Missing ML feature: {feature_name}")
        ordered.append(float(features[feature_name]))

    x = np.asarray([ordered], dtype=float)
    raw_score = float(-bundle["model"].decision_function(x)[0])

    risk = _normalise_risk(
        raw_score,
        bundle["p01"],
        bundle["p99"],
    )
    threshold = float(bundle["threshold"])

    return {
        "raw_score": raw_score,
        "anomaly_score": risk,
        "threshold": threshold,
        "is_alert": risk >= threshold,
        "dataset_name": bundle.get("dataset_name"),
        "code_version": bundle.get("code_version"),
    }
