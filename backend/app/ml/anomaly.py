"""
Anomaly detection layer.

Two complementary detectors are combined:
  - Z-score thresholding on residuals-from-seasonal-profile (catches sudden
    spikes / unexpected drops relative to what's "normal" for that hour/day).
  - Isolation Forest over engineered features (catches multi-dimensional /
    sensor-level oddities that a single-variable z-score would miss).

Findings are merged and de-duplicated by timestamp, keeping the higher score.
"""
from __future__ import annotations

from typing import List, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.services.preprocessing import add_time_features

Z_THRESHOLD = 2.75


def _classify(observed: float, expected: float) -> str:
    if observed > expected:
        return "spike"
    return "drop"


def zscore_anomalies(series: pd.DataFrame) -> List[Dict]:
    df = series.copy()
    df["hour"] = df.index.hour
    df["dow"] = df.index.dayofweek

    bucket_mean = df.groupby(["dow", "hour"])["vehicle_count"].transform("mean")
    bucket_std = df.groupby(["dow", "hour"])["vehicle_count"].transform("std").fillna(df["vehicle_count"].std() or 1.0)
    bucket_std = bucket_std.replace(0, df["vehicle_count"].std() or 1.0)

    z = (df["vehicle_count"] - bucket_mean) / bucket_std

    findings = []
    for ts, zscore, observed, expected in zip(df.index, z, df["vehicle_count"], bucket_mean):
        if abs(zscore) >= Z_THRESHOLD:
            findings.append({
                "timestamp": ts,
                "anomaly_type": _classify(observed, expected),
                "score": round(float(abs(zscore)), 3),
                "observed_value": round(float(observed), 2),
                "expected_value": round(float(expected), 2),
                "method": "zscore",
            })
    return findings


def isolation_forest_anomalies(series: pd.DataFrame, contamination: float = 0.05) -> List[Dict]:
    if len(series) < 20:
        return []  # not enough data for a stable IsolationForest fit

    feats = add_time_features(series)
    X = feats[["vehicle_count", "hour", "dow", "is_weekend", "rolling_mean_3h", "rolling_std_6h"]].values

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    preds = model.fit_predict(X)  # -1 = anomaly, 1 = normal
    scores = -model.score_samples(X)  # higher = more anomalous

    findings = []
    for ts, pred, score, observed, expected in zip(
        feats.index, preds, scores, feats["vehicle_count"], feats["rolling_mean_3h"]
    ):
        if pred == -1:
            findings.append({
                "timestamp": ts,
                "anomaly_type": _classify(observed, expected) if observed != expected else "sensor_error",
                "score": round(float(score), 3),
                "observed_value": round(float(observed), 2),
                "expected_value": round(float(expected), 2),
                "method": "isolation_forest",
            })
    return findings


def detect_anomalies(series: pd.DataFrame) -> List[Dict]:
    """Run both detectors and merge, keeping the highest-confidence finding per timestamp."""
    combined: Dict[pd.Timestamp, Dict] = {}

    for finding in zscore_anomalies(series) + isolation_forest_anomalies(series):
        ts = finding["timestamp"]
        if ts not in combined or finding["score"] > combined[ts]["score"]:
            combined[ts] = finding

    results = sorted(combined.values(), key=lambda f: f["timestamp"])
    return results
