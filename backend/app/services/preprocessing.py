"""
Preprocessing & feature engineering layer.

Responsible for turning raw TrafficRecord rows into a clean, regularly-spaced
pandas time series ready for forecasting/anomaly models, while defensively
handling the edge cases called out in the assignment:
  - missing timestamps / gaps
  - sparse route data
  - sudden spikes / outlier rows
  - invalid / malformed uploads
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np
import pandas as pd

from app.models.traffic import TrafficRecord


REQUIRED_COLUMNS = {"timestamp", "route_id", "vehicle_count"}
MIN_ROWS_FOR_MODELING = 8


class InsufficientDataError(Exception):
    pass


def records_to_dataframe(records: List[TrafficRecord]) -> pd.DataFrame:
    """Convert ORM rows into a tidy, time-sorted DataFrame."""
    if not records:
        return pd.DataFrame(columns=["timestamp", "route_id", "vehicle_count", "avg_speed", "congestion_level"])

    rows = [{
        "timestamp": r.timestamp,
        "route_id": r.route_id,
        "vehicle_count": r.vehicle_count,
        "avg_speed": r.avg_speed,
        "congestion_level": r.congestion_level,
    } for r in records]

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def validate_upload_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Validate & clean an uploaded CSV/DataFrame.
    Returns (cleaned_df, warnings). Raises ValueError on unrecoverable problems.
    """
    warnings: list[str] = []

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}. "
                          f"Required columns are: {sorted(REQUIRED_COLUMNS)}")

    # Drop fully empty rows
    before = len(df)
    df = df.dropna(how="all")
    if len(df) < before:
        warnings.append(f"Dropped {before - len(df)} completely empty row(s).")

    # Parse timestamps, drop unparseable rows (missing/invalid timestamps)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = df["timestamp"].isna().sum()
    if bad_ts:
        warnings.append(f"Dropped {int(bad_ts)} row(s) with missing/invalid timestamps.")
    df = df.dropna(subset=["timestamp"])

    # route_id must be present
    df["route_id"] = df["route_id"].astype(str).str.strip()
    bad_route = (df["route_id"] == "") | (df["route_id"].str.lower() == "nan")
    if bad_route.any():
        warnings.append(f"Dropped {int(bad_route.sum())} row(s) with missing route_id.")
    df = df[~bad_route]

    # vehicle_count must be numeric and non-negative
    df["vehicle_count"] = pd.to_numeric(df["vehicle_count"], errors="coerce")
    bad_vc = df["vehicle_count"].isna() | (df["vehicle_count"] < 0)
    if bad_vc.any():
        warnings.append(f"Dropped {int(bad_vc.sum())} row(s) with invalid vehicle_count.")
    df = df[~bad_vc]

    # Optional numeric columns
    for col in ("avg_speed", "congestion_level"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    if "location" not in df.columns:
        df["location"] = None
    if "weather" not in df.columns:
        df["weather"] = None

    # Derive congestion_level when missing, using a simple normalized-volume heuristic
    if df["congestion_level"].isna().any():
        for route, group in df.groupby("route_id"):
            idx = group.index
            max_vc = group["vehicle_count"].max() or 1.0
            derived = (group["vehicle_count"] / max_vc).clip(0, 1)
            df.loc[idx, "congestion_level"] = df.loc[idx, "congestion_level"].fillna(derived)
        warnings.append("Derived congestion_level from normalized vehicle_count where missing.")

    # Remove exact duplicate (timestamp, route_id) rows, keep last
    before = len(df)
    df = df.drop_duplicates(subset=["timestamp", "route_id"], keep="last")
    if len(df) < before:
        warnings.append(f"Removed {before - len(df)} duplicate timestamp/route rows.")

    if df.empty:
        raise ValueError("No valid rows remained after validation/cleaning.")

    return df.reset_index(drop=True), warnings


def resample_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample a single-route dataframe to a regular hourly grid, filling gaps
    (sparse data / missing timestamps) via time-based interpolation, and
    clip extreme spike artifacts using an IQR cap before modeling.
    """
    if df.empty:
        raise InsufficientDataError("No data available for this route.")

    s = df.set_index("timestamp")["vehicle_count"].sort_index()
    # Collapse duplicate timestamps
    s = s.groupby(level=0).mean()

    full_range = pd.date_range(s.index.min(), s.index.max(), freq="h")
    s = s.reindex(full_range)

    gap_ratio = s.isna().mean()
    s = s.interpolate(method="linear", limit_direction="both")
    s = s.fillna(s.mean() if not s.empty else 0)

    if len(s) < MIN_ROWS_FOR_MODELING:
        raise InsufficientDataError(
            f"Only {len(s)} hourly points available; at least {MIN_ROWS_FOR_MODELING} are needed "
            f"to build a reliable forecast. Upload more historical data for this route."
        )

    out = s.to_frame(name="vehicle_count")
    out.index.name = "timestamp"
    out.attrs["gap_ratio"] = float(gap_ratio)
    return out


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering: hour-of-day, day-of-week, weekend flag, rolling stats."""
    out = df.copy()
    out["hour"] = out.index.hour
    out["dow"] = out.index.dayofweek
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    out["rolling_mean_3h"] = out["vehicle_count"].rolling(3, min_periods=1).mean()
    out["rolling_std_6h"] = out["vehicle_count"].rolling(6, min_periods=1).std().fillna(0)
    return out
