from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.routes.deps import get_current_user
from app.models import User, UserProfile
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/profile", tags=["profile"])

NON_NULLABLE_FIELDS = {
    "state",
    "age",
    "gender",
    "annual_income",
    "category",
    "occupation",
    "educational_level",
    "is_student",
    "owns_land",
    "land_area_hectares",
    "employment_status",
    "is_disabled",
    "disability_percentage",
}


class ProfileUpdate(BaseModel):
    """Partial profile update.

    Every field is optional so the chat orchestrator can send only the values
    it actually extracted instead of failing with a 422 response.
    """

    full_name: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = None
    district: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = None
    annual_income: Optional[float] = Field(default=None, ge=0)
    category: Optional[str] = None
    occupation: Optional[str] = None
    educational_level: Optional[str] = None
    is_student: Optional[bool] = None
    owns_land: Optional[bool] = None
    land_area_hectares: Optional[float] = Field(default=None, ge=0)
    employment_status: Optional[str] = None
    is_disabled: Optional[bool] = None
    disability_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    disability_type: Optional[str] = None
    has_ration_card: Optional[bool] = None
    is_rural: Optional[bool] = None
    owns_house: Optional[bool] = None
    family_beneficiary_count: Optional[int] = Field(default=None, ge=0)
    has_business_plan: Optional[bool] = None
    is_government_employee: Optional[bool] = None


def get_or_create_profile(session: Session, user_id: int) -> UserProfile:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


@router.get("")
def get_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return get_or_create_profile(session, current_user.id)


@router.get("/me")
def get_consumer_identity(
    current_user: User = Depends(get_current_user),
):
    """Returns the unique consumer identity details for display."""
    consumer_id = f"SAR-{current_user.id:04d}"
    return {
        "consumer_id": consumer_id,
        "email": current_user.email,
        "user_id": current_user.id,
    }


@router.put("")
def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    profile = get_or_create_profile(session, current_user.id)
    updates = profile_in.model_dump(exclude_unset=True)

    for field, value in updates.items():
        if value is None and field not in {
            "full_name",
            "district",
            "disability_type",
            "has_ration_card",
            "is_rural",
            "owns_house",
            "family_beneficiary_count",
            "has_business_plan",
            "is_government_employee",
        }:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                if field in NON_NULLABLE_FIELDS:
                    continue
                value = None
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
