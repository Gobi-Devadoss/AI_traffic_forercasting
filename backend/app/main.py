from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.utils.seed_data import ensure_default_admin

from app.api.routes import auth, traffic, forecast, anomaly, optimization, simulation, admin, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and bootstrap a default admin account on startup.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Full-stack AI-powered traffic & mobility forecasting platform: "
        "time-series forecasting, congestion alerts, anomaly detection, "
        "a mobility optimization engine, and scenario simulation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(traffic.router)
app.include_router(forecast.router)
app.include_router(anomaly.router)
app.include_router(optimization.router)
app.include_router(simulation.router)
app.include_router(alerts.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "docs": "/docs",
        "default_admin_hint": (
            f"If this is a fresh install, an admin account was auto-created: "
            f"username='{settings.DEFAULT_ADMIN_USERNAME}'. Check README for the password, "
            f"and change it immediately after first login."
        ),
    }


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "healthy"}
