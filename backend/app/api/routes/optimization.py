from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.traffic import TrafficRecord
from app.schemas.traffic import OptimizationRecommendation
from app.utils.route_data import get_route_hourly_series
from app.services.preprocessing import records_to_dataframe, resample_hourly, InsufficientDataError
from app.services.optimization import generate_recommendations

router = APIRouter(prefix="/api/optimization", tags=["Mobility Optimization"])


@router.get("/recommendations", response_model=OptimizationRecommendation)
def recommendations(
    route_id: str,
    compare_routes: Optional[List[str]] = Query(default=None, description="Other route IDs to load-balance against"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    series = get_route_hourly_series(db, route_id)

    sibling_routes = {}
    if compare_routes:
        for rid in compare_routes:
            if rid == route_id:
                continue
            records = (
                db.query(TrafficRecord)
                .filter(TrafficRecord.route_id == rid)
                .order_by(TrafficRecord.timestamp.asc())
                .all()
            )
            if not records:
                continue
            try:
                df = records_to_dataframe(records)
                sibling_routes[rid] = resample_hourly(df)
            except InsufficientDataError:
                continue

    result = generate_recommendations(route_id, series, sibling_routes or None)
    return OptimizationRecommendation(**result)
