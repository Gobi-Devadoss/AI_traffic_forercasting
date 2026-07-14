from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session
import pandas as pd

from app.models.traffic import TrafficRecord
from app.services.preprocessing import (
    records_to_dataframe,
    resample_hourly,
    InsufficientDataError,
)


def get_route_hourly_series(db: Session, route_id: str) -> pd.DataFrame:
    """Fetch a route's raw records and return a clean, gap-filled hourly series."""
    records: List[TrafficRecord] = (
        db.query(TrafficRecord)
        .filter(TrafficRecord.route_id == route_id)
        .order_by(TrafficRecord.timestamp.asc())
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail=f"No traffic data found for route '{route_id}'.")

    df = records_to_dataframe(records)
    try:
        return resample_hourly(df)
    except InsufficientDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
