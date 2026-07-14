from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.traffic import SimulationRun
from app.schemas.traffic import SimulationRequest, SimulationResponse
from app.utils.route_data import get_route_hourly_series
from app.services.simulation import run_simulation, SCENARIO_PROFILES

router = APIRouter(prefix="/api/simulation", tags=["Scenario Simulation"])


@router.get("/scenarios", response_model=List[str])
def list_scenarios():
    return list(SCENARIO_PROFILES.keys())


@router.post("/run", response_model=SimulationResponse)
def run(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.scenario_type not in SCENARIO_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario_type. Choose one of: {list(SCENARIO_PROFILES)}",
        )

    series = get_route_hourly_series(db, payload.route_id)
    result = run_simulation(
        route_id=payload.route_id,
        baseline_series=series,
        scenario_type=payload.scenario_type,
        intensity=payload.intensity,
        duration_hours=payload.duration_hours,
        affected_alternate_routes=payload.affected_alternate_routes,
    )

    db.add(SimulationRun(
        user_id=current_user.id,
        route_id=payload.route_id,
        scenario_type=payload.scenario_type,
        params=payload.model_dump(),
        results=result,
    ))
    db.commit()

    return SimulationResponse(**result)


@router.get("/history")
def simulation_history(
    route_id: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(SimulationRun)
    if route_id:
        q = q.filter(SimulationRun.route_id == route_id)
    rows = q.order_by(SimulationRun.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "route_id": r.route_id,
            "scenario_type": r.scenario_type,
            "params": r.params,
            "results": r.results,
            "created_at": r.created_at,
        }
        for r in rows
    ]
