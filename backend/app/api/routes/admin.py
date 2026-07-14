from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.models.traffic import TrafficRecord, ForecastResult, Alert, AnomalyRecord, SimulationRun
from app.schemas.user import UserOut, UserRoleUpdate, UserStatusUpdate
from app.utils.seed_data import seed_routes

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post("/seed-demo-data")
def seed_demo_data(
    days: int = 30,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Populate the database with synthetic multi-route traffic history so
    forecasting/anomaly/simulation features can be explored without a real dataset."""
    if days < 3 or days > 180:
        raise HTTPException(status_code=400, detail="days must be between 3 and 180")
    result = seed_routes(db, days=days)
    return {"detail": "Demo data seeded successfully", **result}


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and payload.role.value != "admin":
        raise HTTPException(status_code=400, detail="You cannot demote your own account")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/status", response_model=UserOut)
def update_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}


@router.get("/stats")
def platform_stats(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "total_admins": db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0,
        "total_traffic_records": db.query(func.count(TrafficRecord.id)).scalar() or 0,
        "total_forecasts_generated": db.query(func.count(ForecastResult.id)).scalar() or 0,
        "total_alerts": db.query(func.count(Alert.id)).scalar() or 0,
        "total_anomalies": db.query(func.count(AnomalyRecord.id)).scalar() or 0,
        "total_simulations": db.query(func.count(SimulationRun.id)).scalar() or 0,
    }
