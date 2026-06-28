from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.routes.deps import get_current_user
from app.models import User, ChatMessage
from app.agents.orchestrator import MultiAgentOrchestrator
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/chat", tags=["chat"])
orchestrator = MultiAgentOrchestrator()

class MessageIn(BaseModel):
    message: str
    language: str = "en"
    eli15_mode: bool = False

@router.get("/history", response_model=List[ChatMessage])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Retrieve user chat message logs."""
    return session.exec(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()

@router.post("/message")
def send_chat_message(
    payload: MessageIn,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Send message to the Multi-Agent collaborative casework navigator."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    result = orchestrator.process_chat_message(
        session=session,
        user_id=current_user.id,
        message=payload.message,
        language=payload.language,
        eli15_mode=payload.eli15_mode
    )
    return result
