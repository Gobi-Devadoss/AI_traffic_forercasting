"""
Generates realistic synthetic traffic data so the platform can be explored
immediately without needing a real-world dataset. Run standalone with:

    python -m app.utils.seed_data

or call `seed_routes()` from an admin endpoint / test fixture.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.models.traffic import TrafficRecord
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.core.config import settings

DEFAULT_ROUTES = ["Route-A", "Route-B", "Route-C", "Route-D"]


def _synthesize_route(route_id: str, days: int, base_volume: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    index = pd.date_range(start, end, freq="h")

    hours = index.hour.values
    dows = index.dayofweek.values

    # Morning + evening commute peaks, quieter on weekends
    morning_peak = np.exp(-((hours - 8) ** 2) / (2 * 1.6 ** 2))
    evening_peak = np.exp(-((hours - 18) ** 2) / (2 * 2.0 ** 2))
    weekday_factor = np.where(dows < 5, 1.0, 0.55)

    seasonal = (0.4 * morning_peak + 0.55 * evening_peak + 0.25) * weekday_factor
    trend = np.linspace(0, 0.05, len(index))  # slight upward trend over the window
    noise = rng.normal(0, 0.05, len(index))

    volume = base_volume * (0.5 + seasonal + trend) * (1 + noise)
    volume = np.clip(volume, 5, None)

    # Inject a handful of anomalies: spikes and drops (simulated events/incidents)
    n_anomalies = max(2, len(index) // 150)
    anomaly_idx = rng.choice(len(index), size=n_anomalies, replace=False)
    for i in anomaly_idx:
        if rng.random() < 0.5:
            volume[i] *= rng.uniform(1.8, 2.6)  # spike (e.g. event surge)
        else:
            volume[i] *= rng.uniform(0.15, 0.4)  # unexpected drop (e.g. sensor fault/closure)

    avg_speed = np.clip(65 - (volume / volume.max()) * 45 + rng.normal(0, 2, len(index)), 8, 70)
    congestion = np.clip(volume / (volume.max() * 0.9), 0, 1.4)

    return pd.DataFrame({
        "timestamp": index,
        "route_id": route_id,
        "location": f"{route_id} corridor",
        "vehicle_count": volume.round(1),
        "avg_speed": avg_speed.round(1),
        "congestion_level": congestion.round(3),
        "weather": rng.choice(["clear", "clear", "clear", "rain", "cloudy"], size=len(index)),
    })


def seed_routes(db: Session, days: int = 30, routes=None) -> dict:
    routes = routes or DEFAULT_ROUTES
    total_inserted = 0
    for i, route_id in enumerate(routes):
        base_volume = random.uniform(150, 500)
        df = _synthesize_route(route_id, days=days, base_volume=base_volume, seed=i + 42)
        records = [
            TrafficRecord(
                timestamp=row.timestamp.to_pydatetime(),
                route_id=row.route_id,
                location=row.location,
                vehicle_count=row.vehicle_count,
                avg_speed=row.avg_speed,
                congestion_level=row.congestion_level,
                weather=row.weather,
                source="simulated",
            )
            for row in df.itertuples(index=False)
        ]
        db.bulk_save_objects(records)
        total_inserted += len(records)
    db.commit()
    return {"routes": routes, "records_inserted": total_inserted, "days": days}


def ensure_default_admin(db: Session) -> None:
    """Create a default admin account on first startup if none exists yet."""
    admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if admin_exists:
        return
    admin = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        email=settings.DEFAULT_ADMIN_EMAIL,
        hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        ensure_default_admin(session)
        result = seed_routes(session)
        print(f"Seeded {result['records_inserted']} records across routes: {result['routes']}")
        print(f"Default admin login -> username: {settings.DEFAULT_ADMIN_USERNAME}, "
              f"password: {settings.DEFAULT_ADMIN_PASSWORD}")
    finally:
        session.close()
