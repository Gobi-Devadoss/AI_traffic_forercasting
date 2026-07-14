from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class TrafficRecordIn(BaseModel):
    timestamp: datetime
    route_id: str
    location: Optional[str] = None
    vehicle_count: float
    avg_speed: Optional[float] = None
    congestion_level: Optional[float] = None
    weather: Optional[str] = None


class TrafficRecordOut(TrafficRecordIn):
    id: int
    source: str

    class Config:
        from_attributes = True


class UploadSummary(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    routes: List[str]
    warnings: List[str] = []


class ForecastRequest(BaseModel):
    route_id: str
    horizon: str = Field(default="24h", description="24h | 7d | peak")
    model_type: str = Field(default="auto", description="auto | moving_average | linear | seasonal")


class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_volume: float
    congestion_level: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    route_id: str
    forecast_type: str
    model_used: str
    horizon: str
    generated_at: datetime
    accuracy_mae: Optional[float] = None
    accuracy_mape: Optional[float] = None
    points: List[ForecastPoint]
    alerts: List[str] = []


class PeakHourResponse(BaseModel):
    route_id: str
    peak_hours: List[Dict[str, Any]]


class AlertOut(BaseModel):
    id: int
    route_id: str
    alert_type: str
    severity: str
    message: str
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyOut(BaseModel):
    id: int
    route_id: str
    timestamp: datetime
    anomaly_type: str
    score: float
    observed_value: float
    expected_value: Optional[float] = None
    method: str

    class Config:
        from_attributes = True


class OptimizationRecommendation(BaseModel):
    route_id: str
    recommendations: List[str]
    best_travel_windows: List[Dict[str, Any]]
    load_balancing: List[str]


class SimulationRequest(BaseModel):
    route_id: str
    scenario_type: str = Field(description="road_closure | rain | event | load_increase")
    intensity: float = Field(default=1.0, ge=0.0, le=5.0, description="Scenario severity multiplier")
    duration_hours: int = Field(default=3, ge=1, le=48)
    affected_alternate_routes: Optional[List[str]] = None


class SimulationResponse(BaseModel):
    route_id: str
    scenario_type: str
    congestion_impact_pct: float
    delay_minutes: float
    travel_time_change_pct: float
    baseline_volume: float
    projected_volume: float
    affected_routes: List[Dict[str, Any]]
    narrative: str


class DashboardSummary(BaseModel):
    total_records: int
    total_routes: int
    active_alerts: int
    recent_anomalies: int
    routes: List[str]
