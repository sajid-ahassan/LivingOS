from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


FEATURES = [
    "event_count",
    "failed_login_count",
    "failed_login_ratio",
    "command_count",
    "file_event_count",
    "http_count",
    "email_count",
    "device_count",
    "session_count",
    "unique_agents",
    "unique_decoders",
    "unique_actions",
    "high_severity_count",
    "high_severity_ratio",
    "off_hours_count",
    "off_hours_ratio",
]


def _safe_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _prepare_events(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    required = {
        "Agent_name",
        "User",
        "Timestamp",
        "Decoder_name",
        "Level",
        "Activity",
        "Action",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required SPEDIA columns: {missing}")

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce",
        utc=False,
    )
    df = df[df["Timestamp"].notna()].copy()

    for col in [
        "Agent_name",
        "User",
        "Decoder_name",
        "Activity",
        "Action",
    ]:
        df[col] = _safe_text(df[col])

    df = df[df["User"] != ""].copy()

    df["Level"] = pd.to_numeric(df["Level"], errors="coerce")

    df["window_start"] = df["Timestamp"].dt.floor("h")
    df["hour_of_day"] = df["Timestamp"].dt.hour

    action_lower = df["Action"].str.lower()
    activity_lower = df["Activity"].str.lower()

    df["failed_login"] = (
        action_lower.str.contains("failed login", regex=False)
        | action_lower.str.contains("login failed", regex=False)
    ).astype("int8")

    df["is_command"] = activity_lower.eq("command").astype("int8")
    df["is_file"] = activity_lower.eq("file").astype("int8")
    df["is_http"] = activity_lower.eq("http").astype("int8")
    df["is_email"] = activity_lower.eq("email").astype("int8")
    df["is_device"] = activity_lower.eq("device").astype("int8")
    df["is_session"] = activity_lower.eq("session").astype("int8")

    # Wazuh-style higher-severity events. Used as an observed event
    # characteristic, not as a ground-truth label.
    df["high_severity"] = (df["Level"].fillna(0) >= 10).astype("int8")

    # 00:00-05:59 and 22:00-23:59.
    df["off_hours"] = (
        (df["hour_of_day"] < 6) | (df["hour_of_day"] >= 22)
    ).astype("int8")

    # Conservative evaluation label only. It is NOT included in FEATURES.
    df["is_known_attack"] = (
        df["Agent_name"]
        .str.lower()
        .str.startswith("atacante_")
    ).astype("int8")

    return df


def aggregate_windows(
    input_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    df = _prepare_events(input_path)

    grouped = (
        df.groupby(["User", "window_start"], sort=True)
        .agg(
            event_count=("Action", "size"),
            failed_login_count=("failed_login", "sum"),
            command_count=("is_command", "sum"),
            file_event_count=("is_file", "sum"),
            http_count=("is_http", "sum"),
            email_count=("is_email", "sum"),
            device_count=("is_device", "sum"),
            session_count=("is_session", "sum"),
            unique_agents=("Agent_name", "nunique"),
            unique_decoders=("Decoder_name", "nunique"),
            unique_actions=("Action", "nunique"),
            high_severity_count=("high_severity", "sum"),
            off_hours_count=("off_hours", "sum"),
            is_known_attack=("is_known_attack", "max"),
        )
        .reset_index()
    )

    grouped["failed_login_ratio"] = (
        grouped["failed_login_count"]
        / grouped["event_count"].clip(lower=1)
    )

    grouped["high_severity_ratio"] = (
        grouped["high_severity_count"]
        / grouped["event_count"].clip(lower=1)
    )

    grouped["off_hours_ratio"] = (
        grouped["off_hours_count"]
        / grouped["event_count"].clip(lower=1)
    )

    ordered = [
        "User",
        "window_start",
        *FEATURES,
        "is_known_attack",
    ]
    grouped = grouped[ordered].sort_values(
        ["window_start", "User"]
    ).reset_index(drop=True)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(output_path, index=False)

    print(f"Raw events: {len(df):,}")
    print(f"User-hour windows: {len(grouped):,}")
    print(
        "Known-attack windows:",
        int(grouped["is_known_attack"].sum()),
    )
    print(f"Saved: {output_path}")

    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build LivingOps user-hour features from SPEDIA."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    aggregate_windows(
        input_path=args.input,
        output_path=args.out,
    )


if __name__ == "__main__":
    main()
