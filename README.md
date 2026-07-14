# AI-Based Traffic & Mobility Forecasting System

A full-stack platform for traffic volume forecasting, congestion/risk alerts,
anomaly detection, mobility optimization, and scenario simulation.

```
traffic-forecast/
  backend/     FastAPI + SQLAlchemy + scikit-learn ML services
  frontend/    React (Vite) dashboard with interactive charts
  docker-compose.yml
```

## Fastest way to try it (local, no Docker)

**1. Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.utils.seed_data      # optional: generates 30 days of demo data for 4 routes
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs
Default admin (auto-created on first run): username `admin`, password `Admin@12345`
(also see `.env` — change this immediately for any real deployment).

**2. Frontend**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
App: http://localhost:5173 — log in with the admin above, or register a new account
(the very first registered user is auto-promoted to admin).

If you didn't run the seed script, go to **Data Upload** in the app and either
upload your own CSV (`timestamp, route_id, vehicle_count, ...`) or click
**Seed Demo Data** (admin only) to generate synthetic history instantly.

## Docker

```bash
docker compose up --build
```
Backend: http://localhost:8000 · Frontend: http://localhost:5173

Note: the frontend Docker image is a static production build, so
`VITE_API_BASE_URL` must be correct at *build* time — edit
`frontend/.env` (or the Dockerfile `ARG`/`ENV`) before `docker compose build`
if your backend isn't on `localhost:8000`.

## What's implemented

- **Forecasting**: 24h / 7-day hourly forecasts, auto model selection (moving
  average / linear regression on cyclical time features / seasonal-naive),
  backtested MAE & MAPE, confidence bands, peak-hour analytics.
- **Congestion & risk alerts**: auto-derived from each forecast (congestion
  windows, volume spikes, volatile/high-congestion "accident risk" pattern).
- **Anomaly detection**: Z-score (seasonal-bucket residuals) + Isolation
  Forest, merged and visualized.
- **Mobility optimization engine**: best travel windows, congestion-reduction
  tips, route load-balancing suggestions (when comparing against sibling routes).
- **Scenario simulation**: road closures, rain, event surges, load increases —
  using a BPR-style volume/capacity delay curve for congestion & delay estimates.
- **Auth & admin**: JWT auth, `user`/`admin` roles, admin panel (manage users,
  view platform stats, seed demo data).
- **Data ingestion**: CSV upload with validation for missing timestamps,
  invalid rows, sparse data, and duplicate points — reports what was skipped
  and why instead of failing outright.

See `backend/README.md` for the full API reference and architecture notes.
