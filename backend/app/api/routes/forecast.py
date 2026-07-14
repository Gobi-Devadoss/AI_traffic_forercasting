from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.traffic import ForecastResult, Alert
from app.schemas.traffic import ForecastResponse, ForecastPoint, PeakHourResponse
from app.utils.route_data import get_route_hourly_series
from app.ml.forecasting import generate_forecast, volume_to_congestion, compute_peak_hours
from app.services.alerts import build_alerts

router = APIRouter(prefix="/api/forecast", tags=["Forecasting"])

HORIZON_HOURS = {
    "24h": 24,
    "7d": 24 * 7,
}


@router.get("/generate", response_model=ForecastResponse)
def generate(
    route_id: str,
    horizon: str = Query(default="24h", description="24h | 7d"),
    model_type: str = Query(default="auto", description="auto | moving_average | linear | seasonal"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if horizon not in HORIZON_HOURS:
        horizon = "24h"
    horizon_hours = HORIZON_HOURS[horizon]

    series = get_route_hourly_series(db, route_id)
    result = generate_forecast(series, horizon_hours, model_type)

    historical_max = float(series["vehicle_count"].max())
    historical_mean = float(series["vehicle_count"].mean())
    congestion = volume_to_congestion(result.predicted, historical_max)

    points = [
        ForecastPoint(
            timestamp=ts,
            predicted_volume=round(float(v), 1),
            congestion_level=round(float(c), 3),
            lower_bound=round(float(lo), 1),
            upper_bound=round(float(hi), 1),
        )
        for ts, v, c, lo, hi in zip(result.timestamps, result.predicted, congestion, result.lower, result.upper)
    ]

    point_dicts = [p.model_dump() for p in points]
    alert_dicts = build_alerts(route_id, point_dicts, historical_mean)

    forecast_type = "hourly_24h" if horizon == "24h" else "daily_7d"

    db_result = ForecastResult(
        route_id=route_id,
        forecast_type=forecast_type,
        model_used=result.model_used,
        horizon=horizon,
        accuracy_mae=result.mae,
        accuracy_mape=result.mape,
        data=[p.model_dump(mode="json") for p in points],
        generated_by=current_user.id,
    )
    db.add(db_result)

    for a in alert_dicts:
        db.add(Alert(**a))
    db.commit()

    return ForecastResponse(
        route_id=route_id,
        forecast_type=forecast_type,
        model_used=result.model_used,
        horizon=horizon,
        generated_at=db_result.generated_at,
        accuracy_mae=result.mae,
        accuracy_mape=result.mape,
        points=points,
        alerts=[a["message"] for a in alert_dicts],
    )


@router.get("/peak-hours", response_model=PeakHourResponse)
def peak_hours(
    route_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    series = get_route_hourly_series(db, route_id)
    peaks = compute_peak_hours(series, top_n=5)
    return PeakHourResponse(route_id=route_id, peak_hours=peaks)


@router.get("/history")
def forecast_history(
    route_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return past forecast runs for a route (for accuracy tracking / audit)."""
    rows = (
        db.query(ForecastResult)
        .filter(ForecastResult.route_id == route_id)
        .order_by(ForecastResult.generated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "forecast_type": r.forecast_type,
            "model_used": r.model_used,
            "horizon": r.horizon,
            "generated_at": r.generated_at,
            "accuracy_mae": r.accuracy_mae,
            "accuracy_mape": r.accuracy_mape,
        }
        for r in rows
    ]
