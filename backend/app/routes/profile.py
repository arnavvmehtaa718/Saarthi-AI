from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.routes.deps import get_current_user
from app.models import User, UserProfile
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/profile", tags=["profile"])

class ProfileUpdate(BaseModel):
    state: str
    district: str | None = None
    age: int
    gender: str
    annual_income: float
    category: str
    occupation: str
    is_student: bool
    owns_land: bool
    land_area_hectares: float
    is_disabled: bool
    disability_percentage: float
    disability_type: str | None = None

@router.get("")
def get_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile

@router.get("/me")
def get_consumer_identity(
    current_user: User = Depends(get_current_user),
):
    """Returns the unique consumer identity details for display."""
    consumer_id = f"SAR-{current_user.id:04d}"
    return {
        "consumer_id": consumer_id,
        "email": current_user.email,
        "user_id": current_user.id
    }

@router.put("")
def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == current_user.id)).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
        
    # Update values
    for field, value in profile_in.model_dump().items():
        setattr(profile, field, value)
        
    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
