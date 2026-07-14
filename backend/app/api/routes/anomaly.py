from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.traffic import AnomalyRecord
from app.schemas.traffic import AnomalyOut
from app.utils.route_data import get_route_hourly_series
from app.ml.anomaly import detect_anomalies

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])


@router.get("/detect", response_model=List[AnomalyOut])
def detect(
    route_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run z-score + Isolation Forest detection over a route's historical series,
    persist new findings, and return them."""
    series = get_route_hourly_series(db, route_id)
    findings = detect_anomalies(series)

    saved = []
    for f in findings:
        exists = (
            db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.route_id == route_id,
                AnomalyRecord.timestamp == f["timestamp"],
                AnomalyRecord.method == f["method"],
            )
            .first()
        )
        if exists:
            saved.append(exists)
            continue
        record = AnomalyRecord(route_id=route_id, **f)
        db.add(record)
        saved.append(record)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved


@router.get("/list", response_model=List[AnomalyOut])
def list_anomalies(
    route_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(AnomalyRecord)
    if route_id:
        q = q.filter(AnomalyRecord.route_id == route_id)
    return q.order_by(AnomalyRecord.timestamp.desc()).limit(limit).all()
