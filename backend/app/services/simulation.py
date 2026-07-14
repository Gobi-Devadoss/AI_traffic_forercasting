"""
Scenario Simulation System.

Applies deterministic, explainable multipliers to a route's baseline
traffic profile to estimate the impact of hypothetical scenarios
(road closures, heavy rain, event surges, general load increases).
Multipliers are informed by commonly cited transportation-engineering
rules of thumb (e.g. capacity-restriction -> delay via a simplified
BPR-style volume/capacity delay curve) — not a claim of real-world
precision, but a reasonable, tunable approximation suitable for a
what-if planning tool.
"""
from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np
import pandas as pd

# Base scenario effect definitions: (volume_multiplier, capacity_multiplier)
SCENARIO_PROFILES = {
    "road_closure": {"volume_mult": 1.0, "capacity_mult": 0.35, "reroute_share": 0.6},
    "rain": {"volume_mult": 0.92, "capacity_mult": 0.75, "reroute_share": 0.1},
    "event": {"volume_mult": 1.45, "capacity_mult": 0.9, "reroute_share": 0.25},
    "load_increase": {"volume_mult": 1.25, "capacity_mult": 1.0, "reroute_share": 0.15},
}


def _bpr_delay_factor(volume_capacity_ratio: float, alpha: float = 0.15, beta: float = 4.0) -> float:
    """Bureau of Public Roads delay function: travel_time = free_flow * (1 + alpha*(v/c)^beta)."""
    ratio = max(0.0, volume_capacity_ratio)
    return 1 + alpha * (ratio ** beta)


def run_simulation(
    route_id: str,
    baseline_series: pd.DataFrame,
    scenario_type: str,
    intensity: float = 1.0,
    duration_hours: int = 3,
    affected_alternate_routes: Optional[List[str]] = None,
) -> Dict:
    if scenario_type not in SCENARIO_PROFILES:
        raise ValueError(
            f"Unknown scenario_type '{scenario_type}'. Choose one of: {list(SCENARIO_PROFILES)}"
        )

    profile = SCENARIO_PROFILES[scenario_type]
    baseline_volume = float(baseline_series["vehicle_count"].mean()) if not baseline_series.empty else 100.0
    baseline_capacity = float(baseline_series["vehicle_count"].quantile(0.95)) if not baseline_series.empty else baseline_volume * 1.3
    baseline_capacity = max(baseline_capacity, baseline_volume * 1.05, 1.0)

    volume_mult = 1 + (profile["volume_mult"] - 1) * intensity
    capacity_mult = 1 - (1 - profile["capacity_mult"]) * intensity
    capacity_mult = max(0.05, capacity_mult)

    projected_volume = baseline_volume * volume_mult
    projected_capacity = baseline_capacity * capacity_mult

    baseline_vc_ratio = baseline_volume / baseline_capacity
    projected_vc_ratio = projected_volume / projected_capacity

    baseline_delay_factor = _bpr_delay_factor(baseline_vc_ratio)
    projected_delay_factor = _bpr_delay_factor(projected_vc_ratio)

    free_flow_minutes = 15.0  # assumed nominal free-flow travel time for the route segment
    baseline_travel_time = free_flow_minutes * baseline_delay_factor
    projected_travel_time = free_flow_minutes * projected_delay_factor

    delay_minutes = round(max(0.0, projected_travel_time - baseline_travel_time), 1)
    travel_time_change_pct = round(
        ((projected_travel_time - baseline_travel_time) / baseline_travel_time) * 100, 1
    ) if baseline_travel_time > 0 else 0.0
    congestion_impact_pct = round(
        ((projected_vc_ratio - baseline_vc_ratio) / max(baseline_vc_ratio, 1e-6)) * 100, 1
    )

    affected_routes = []
    if affected_alternate_routes:
        reroute_share = profile["reroute_share"] * intensity
        diverted_volume = projected_volume * min(reroute_share, 0.9)
        per_route_share = diverted_volume / len(affected_alternate_routes)
        for alt in affected_alternate_routes:
            affected_routes.append({
                "route_id": alt,
                "additional_volume": round(per_route_share, 1),
                "note": f"Estimated additional load from traffic diverted off Route {route_id}.",
            })

    scenario_labels = {
        "road_closure": "road closure",
        "rain": "heavy rain / weather event",
        "event": "festival / large event",
        "load_increase": "sustained increase in vehicle load",
    }
    narrative = (
        f"Simulating a {scenario_labels.get(scenario_type, scenario_type)} on Route {route_id} "
        f"(intensity {intensity}x, {duration_hours}h duration): projected volume moves from "
        f"~{baseline_volume:.0f} to ~{projected_volume:.0f} vehicles/hr, with average travel time "
        f"increasing by ~{delay_minutes:.1f} minutes ({travel_time_change_pct:+.1f}%)."
    )

    return {
        "route_id": route_id,
        "scenario_type": scenario_type,
        "congestion_impact_pct": congestion_impact_pct,
        "delay_minutes": delay_minutes,
        "travel_time_change_pct": travel_time_change_pct,
        "baseline_volume": round(baseline_volume, 1),
        "projected_volume": round(projected_volume, 1),
        "affected_routes": affected_routes,
        "narrative": narrative,
    }
