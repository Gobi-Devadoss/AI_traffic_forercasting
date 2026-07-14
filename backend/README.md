# AI Traffic & Mobility Forecasting — Backend

FastAPI backend implementing:

- **Auth**: register/login (JWT), role-based access (`user` / `admin`), admin panel APIs
- **Forecasting**: hourly (24h) and daily (7d) traffic volume forecasts, peak-hour detection,
  auto-selected model (moving average / linear regression / seasonal-naive) with backtested
  MAE/MAPE accuracy
- **Congestion & risk alerts**: auto-generated from forecasts (congestion windows, volume
  spikes, accident-risk pattern flags)
- **Anomaly detection**: Z-score + Isolation Forest, merged and de-duplicated
- **Mobility optimization engine**: best travel windows, congestion-reduction tips, route
  load-balancing suggestions
- **Scenario simulation**: road closures, rain, event surges, load increases — with
  congestion impact / delay / travel-time-change estimates
- **Data upload**: CSV upload with validation for missing timestamps, sparse data, invalid
  rows, duplicate points

## Quick start

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # adjust if needed

# (optional) seed synthetic demo data for 4 routes over 30 days
python -m app.utils.seed_data

uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

On first startup, if no admin exists yet, one is auto-created using the
`DEFAULT_ADMIN_*` values in `.env` (defaults: `admin` / `Admin@12345`).
**Change this password immediately in any real deployment.**

Alternatively, the **first user to ever register** via `POST /api/auth/register`
is automatically promoted to `admin`.

## Project layout

```
app/
  core/        # config, DB session, security (JWT/bcrypt), auth dependencies
  models/      # SQLAlchemy models (User, TrafficRecord, ForecastResult, Alert,
               # AnomalyRecord, SimulationRun)
  schemas/     # Pydantic request/response schemas
  services/    # preprocessing, alert generation, optimization engine, simulation engine
  ml/          # forecasting models + anomaly detection models
  api/routes/  # FastAPI routers (auth, traffic, forecast, anomaly, optimization,
               # simulation, alerts, admin)
  utils/       # shared helpers, synthetic demo-data seeder
```

## CSV upload format

```
timestamp,route_id,vehicle_count,avg_speed,congestion_level,location,weather
2026-07-01 08:00:00,Route-A,320,28.5,0.72,Main St,clear
```

Only `timestamp`, `route_id`, and `vehicle_count` are required; the rest are optional
and will be derived/defaulted when missing. Rows with unparseable timestamps, missing
route IDs, or non-numeric vehicle counts are dropped and reported back in the
response's `warnings` list rather than failing the whole upload.

## Key endpoints

| Area | Endpoint |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Data | `POST /api/traffic/upload`, `GET /api/traffic/records`, `GET /api/traffic/routes`, `GET /api/traffic/summary` |
| Forecast | `GET /api/forecast/generate?route_id=&horizon=24h|7d`, `GET /api/forecast/peak-hours` |
| Anomaly | `GET /api/anomaly/detect?route_id=`, `GET /api/anomaly/list` |
| Optimization | `GET /api/optimization/recommendations?route_id=` |
| Simulation | `POST /api/simulation/run`, `GET /api/simulation/scenarios` |
| Alerts | `GET /api/alerts` |
| Admin | `GET /api/admin/users`, `PUT /api/admin/users/{id}/role`, `POST /api/admin/seed-demo-data`, `GET /api/admin/stats` |

All endpoints except `/api/auth/register` and `/api/auth/login` require a Bearer token.

## Notes on the forecasting approach

Instead of hard-requiring Prophet/TensorFlow (heavy, optional installs), the
forecasting layer ships three lightweight, dependency-friendly models — an
exponentially-weighted moving average, a regression on engineered cyclical time
features, and a seasonal-naive model — plus an `auto` mode that backtests all
three on a holdout window and picks the best performer per route. The
`BaseForecaster` interface in `app/ml/forecasting.py` makes it straightforward to
drop in Prophet/ARIMA/LSTM as an additional registered model later without
touching the API layer.
