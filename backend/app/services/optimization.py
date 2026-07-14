"""
Mobility Optimization Engine.

Consumes a forecast + historical profile for a route (and, if available,
sibling routes) to produce human-readable recommendations: best travel
windows, congestion-reduction advice, and route load-balancing suggestions.
This is intentionally rule-based (deterministic, explainable) rather than a
black-box model, since the outputs are meant to be read/acted on by a human.
"""
from __future__ import annotations

from typing import List, Dict, Optional
import numpy as np
import pandas as pd

from app.ml.forecasting import compute_peak_hours


def _best_travel_windows(series: pd.DataFrame, top_n: int = 3) -> List[Dict]:
    df = series.copy()
    df["hour"] = df.index.hour
    profile = df.groupby("hour")["vehicle_count"].mean()
    quietest = profile.sort_values().head(top_n)
    busiest_avg = profile.mean() or 1.0

    windows = []
    for hour, volume in quietest.items():
        reduction_pct = round(max(0.0, (1 - volume / busiest_avg) * 100), 1)
        windows.append({
            "hour": int(hour),
            "label": f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00",
            "avg_volume": round(float(volume), 2),
            "estimated_time_savings_pct": reduction_pct,
        })
    return windows


def generate_recommendations(
    route_id: str,
    series: pd.DataFrame,
    sibling_routes: Optional[Dict[str, pd.DataFrame]] = None,
) -> Dict:
    peak_hours = compute_peak_hours(series, top_n=3)
    best_windows = _best_travel_windows(series, top_n=3)

    recommendations = []
    for p in peak_hours:
        recommendations.append(
            f"Avoid Route {route_id} between {p['label']} — average volume is "
            f"{p['avg_volume']:.0f} vehicles/hr, the busiest window observed."
        )
    for w in best_windows[:2]:
        if w["estimated_time_savings_pct"] > 0:
            recommendations.append(
                f"Travel during {w['label']} to reduce expected travel time by "
                f"~{w['estimated_time_savings_pct']:.0f}% on Route {route_id}."
            )

    load_balancing = []
    if sibling_routes:
        route_loads = {route_id: series["vehicle_count"].mean()}
        for rid, s in sibling_routes.items():
            if not s.empty:
                route_loads[rid] = s["vehicle_count"].mean()

        if len(route_loads) > 1:
            busiest = max(route_loads, key=route_loads.get)
            quietest = min(route_loads, key=route_loads.get)
            if busiest != quietest and route_loads[busiest] > 0:
                diff_pct = (route_loads[busiest] - route_loads[quietest]) / route_loads[busiest] * 100
                if diff_pct > 15:
                    load_balancing.append(
                        f"Redirect a portion of traffic from Route {busiest} to Route {quietest} "
                        f"during peak periods — current load differs by ~{diff_pct:.0f}%."
                    )
    if not load_balancing:
        load_balancing.append(
            "No significant load imbalance detected against other tracked routes; "
            "continue monitoring during peak windows."
        )

    if not recommendations:
        recommendations.append(
            f"Traffic on Route {route_id} looks stable across the observed period — "
            f"no strong peak/off-peak pattern detected yet."
        )

    return {
        "route_id": route_id,
        "recommendations": recommendations,
        "best_travel_windows": best_windows,
        "load_balancing": load_balancing,
    }
