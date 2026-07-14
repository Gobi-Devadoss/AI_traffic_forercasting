import io
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.traffic import TrafficRecord
from app.schemas.traffic import TrafficRecordOut, UploadSummary, TrafficRecordIn, DashboardSummary
from app.models.traffic import Alert, AnomalyRecord
from app.services.preprocessing import validate_upload_dataframe

router = APIRouter(prefix="/api/traffic", tags=["Traffic Data"])


@router.post("/upload", response_model=UploadSummary)
async def upload_traffic_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a CSV of historical traffic data. Expected columns:
    timestamp, route_id, vehicle_count, [location, avg_speed, congestion_level, weather]
    Invalid rows (missing timestamps, bad route ids, non-numeric counts, etc.)
    are dropped and reported back rather than failing the whole upload.
    """
    if not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV file: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file contains no data.")

    rows_received = len(df)
    try:
        clean_df, warnings = validate_upload_dataframe(df)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    records = [
        TrafficRecord(
            timestamp=row.timestamp.to_pydatetime(),
            route_id=row.route_id,
            location=row.location if pd.notna(row.location) else None,
            vehicle_count=float(row.vehicle_count),
            avg_speed=float(row.avg_speed) if pd.notna(row.avg_speed) else None,
            congestion_level=float(row.congestion_level) if pd.notna(row.congestion_level) else None,
            weather=row.weather if pd.notna(row.weather) else None,
            source="upload",
            uploaded_by=current_user.id,
        )
        for row in clean_df.itertuples(index=False)
    ]
    db.bulk_save_objects(records)
    db.commit()

    return UploadSummary(
        rows_received=rows_received,
        rows_inserted=len(records),
        rows_skipped=rows_received - len(records),
        routes=sorted(clean_df["route_id"].unique().tolist()),
        warnings=warnings,
    )


@router.post("/records", response_model=TrafficRecordOut)
def add_single_record(
    payload: TrafficRecordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add one manual traffic record (useful for testing/demo without a CSV)."""
    record = TrafficRecord(
        **payload.model_dump(),
        source="manual",
        uploaded_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/records", response_model=List[TrafficRecordOut])
def list_records(
    route_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = Query(default=500, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(TrafficRecord)
    if route_id:
        q = q.filter(TrafficRecord.route_id == route_id)
    if start:
        q = q.filter(TrafficRecord.timestamp >= start)
    if end:
        q = q.filter(TrafficRecord.timestamp <= end)
    return q.order_by(TrafficRecord.timestamp.desc()).limit(limit).all()


@router.get("/routes", response_model=List[str])
def list_routes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(TrafficRecord.route_id).distinct().all()
    return sorted([r[0] for r in rows])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_records = db.query(func.count(TrafficRecord.id)).scalar() or 0
    routes = sorted([r[0] for r in db.query(TrafficRecord.route_id).distinct().all()])
    active_alerts = db.query(func.count(Alert.id)).scalar() or 0
    recent_anomalies = db.query(func.count(AnomalyRecord.id)).scalar() or 0

    return DashboardSummary(
        total_records=total_records,
        total_routes=len(routes),
        active_alerts=active_alerts,
        recent_anomalies=recent_anomalies,
        routes=routes,
    )
