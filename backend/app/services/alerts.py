"""
Congestion / risk alert generation.

Scans a generated forecast for windows that cross congestion thresholds
or represent a sharp jump versus the recent historical baseline, and turns
them into short, human-readable alert strings (and DB-persistable dicts).
"""
from __future__ import annotations

from typing import List, Dict
import numpy as np
import pandas as pd

CONGESTION_HIGH = 0.8
CONGESTION_MEDIUM = 0.6
SPIKE_INCREASE_THRESHOLD_PCT = 30.0


def build_alerts(route_id: str, forecast_points: List[dict], historical_mean: float) -> List[Dict]:
    """
    forecast_points: list of {timestamp, predicted_volume, congestion_level}
    Returns a list of alert dicts ready to persist / return to the client.
    """
    alerts: List[Dict] = []
    if not forecast_points:
        return alerts

    # --- Congestion window detection: group consecutive high-congestion hours ---
    window_start = None
    window_end = None
    window_severity = None

    def flush_window():
        if window_start is not None:
            sev_label = "High" if window_severity == "high" else "Medium"
            alerts.append({
                "route_id": route_id,
                "alert_type": "congestion",
                "severity": window_severity,
                "message": (
                    f"{sev_label} congestion expected on Route {route_id} between "
                    f"{window_start.strftime('%I:%M %p').lstrip('0')} and "
                    f"{window_end.strftime('%I:%M %p').lstrip('0')} on "
                    f"{window_start.strftime('%b %d')}."
                ),
                "window_start": window_start,
                "window_end": window_end,
            })

    for point in forecast_points:
        level = point["congestion_level"]
        ts = point["timestamp"]
        if level >= CONGESTION_HIGH:
            sev = "high"
        elif level >= CONGESTION_MEDIUM:
            sev = "medium"
        else:
            sev = None

        if sev:
            if window_start is None:
                window_start, window_severity = ts, sev
            elif sev != window_severity:
                flush_window()
                window_start, window_severity = ts, sev
            window_end = ts
        else:
            flush_window()
            window_start = window_end = window_severity = None
    flush_window()

    # --- Spike detection: any single hour far above historical average ---
    baseline = historical_mean or 1.0
    for point in forecast_points:
        increase_pct = ((point["predicted_volume"] - baseline) / baseline) * 100
        if increase_pct >= SPIKE_INCREASE_THRESHOLD_PCT:
            ts = point["timestamp"]
            alerts.append({
                "route_id": route_id,
                "alert_type": "spike",
                "severity": "high" if increase_pct >= 60 else "medium",
                "message": (
                    f"Traffic volume on Route {route_id} is expected to increase by "
                    f"{increase_pct:.0f}% around {ts.strftime('%I:%M %p').lstrip('0')} on "
                    f"{ts.strftime('%b %d')} compared to typical levels."
                ),
                "window_start": ts,
                "window_end": ts,
            })

    # --- Simple accident-risk pattern flag: sustained high congestion + high volatility ---
    volumes = np.array([p["predicted_volume"] for p in forecast_points])
    if len(volumes) > 3:
        volatility = float(np.std(np.diff(volumes)))
        mean_vol = float(volumes.mean()) or 1.0
        if volatility / mean_vol > 0.35 and np.mean([p["congestion_level"] for p in forecast_points]) >= CONGESTION_MEDIUM:
            alerts.append({
                "route_id": route_id,
                "alert_type": "accident_risk",
                "severity": "medium",
                "message": (
                    f"Route {route_id} shows a volatile, high-congestion pattern over the forecast "
                    f"window — historically associated with elevated accident risk. Consider "
                    f"additional monitoring or advisory signage."
                ),
                "window_start": forecast_points[0]["timestamp"],
                "window_end": forecast_points[-1]["timestamp"],
            })

    return alerts
