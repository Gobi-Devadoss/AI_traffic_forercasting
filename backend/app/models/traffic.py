from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrafficRecord(Base):
    """Raw / historical traffic observation, either uploaded or simulated seed data."""
    __tablename__ = "traffic_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    route_id = Column(String(50), nullable=False, index=True)
    location = Column(String(120), nullable=True)
    vehicle_count = Column(Float, nullable=False, default=0)
    avg_speed = Column(Float, nullable=True)
    congestion_level = Column(Float, nullable=True)  # 0-1 scale, derived if not supplied
    weather = Column(String(50), nullable=True)
    source = Column(String(20), default="upload")  # upload | simulated | api
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ForecastResult(Base):
    """Persisted output of a forecasting run, so results can be listed/audited later."""
    __tablename__ = "forecast_results"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), nullable=False, index=True)
    forecast_type = Column(String(30), nullable=False)  # hourly_24h | daily_7d | peak_hour
    model_used = Column(String(30), nullable=False)
    horizon = Column(String(20), nullable=False)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    accuracy_mae = Column(Float, nullable=True)
    accuracy_mape = Column(Float, nullable=True)
    data = Column(JSON, nullable=False)  # list of {timestamp, predicted_volume, congestion_level}
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class Alert(Base):
    """Generated congestion / risk alert."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(30), nullable=False)  # congestion | spike | accident_risk
    severity = Column(String(10), nullable=False)  # low | medium | high
    message = Column(Text, nullable=False)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AnomalyRecord(Base):
    """Detected anomaly in historical traffic data."""
    __tablename__ = "anomaly_records"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    anomaly_type = Column(String(30), nullable=False)  # spike | drop | sensor_error | event_surge
    score = Column(Float, nullable=False)
    observed_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=True)
    method = Column(String(20), nullable=False)  # zscore | isolation_forest
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SimulationRun(Base):
    """A scenario simulation request and its computed results."""
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    route_id = Column(String(50), nullable=False, index=True)
    scenario_type = Column(String(30), nullable=False)  # road_closure | rain | event | load_increase
    params = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
