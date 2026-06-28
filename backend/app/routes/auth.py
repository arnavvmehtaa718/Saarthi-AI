import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models import User, UserProfile
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegister(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/signup", response_model=Token)
def signup(user_in: UserRegister, session: Session = Depends(get_session)):
    # Check if user already exists
    statement = select(User).where(User.email == user_in.email)
    user_exists = session.exec(statement).first()
    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
        
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Initialize empty profile for user
    profile = UserProfile(user_id=user.id)
    session.add(profile)
    session.commit()
    
    # Generate token
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")

@router.post("/guest", response_model=Token)
def guest_login(session: Session = Depends(get_session)):
    """Create a temporary guest account to allow immediate platform interactions."""
    guest_uuid = str(uuid.uuid4())[:8]
    guest_email = f"guest_{guest_uuid}@saarthi.ai"
    guest_password = str(uuid.uuid4())
    
    hashed_password = get_password_hash(guest_password)
    user = User(email=guest_email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Initialize basic profile
    profile = UserProfile(user_id=user.id)
    session.add(profile)
    session.commit()
    
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")
