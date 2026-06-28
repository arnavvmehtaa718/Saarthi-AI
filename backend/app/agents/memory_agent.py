from typing import Dict, Any, List
from sqlmodel import Session, select
from app.agents.base import BaseAgent
from app.models import UserProfile, UserScheme, Document, ChatMessage

class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Memory Agent",
            description="Manages profile records, saved schemes, chat history logs, and document metadata."
        )

    def load_chat_context(self, session: Session, user_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent chat history for session context."""
        statement = select(ChatMessage).where(ChatMessage.user_id == user_id).order_by(ChatMessage.created_at.desc()).limit(limit)
        messages = session.exec(statement).all()
        # Return chronologically ascending (oldest first)
        messages.reverse()
        return [{"role": msg.role, "content": msg.content, "agent": msg.agent_name} for msg in messages]

    def save_chat_message(self, session: Session, user_id: int, role: str, content: str, agent_name: str = None) -> ChatMessage:
        """Commit a new chat message to history."""
        msg = ChatMessage(user_id=user_id, role=role, content=content, agent_name=agent_name)
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return msg

    def load_profile_data(self, session: Session, user_id: int) -> Dict[str, Any]:
        """Fetch the serialized user profile dictionary."""
        statement = select(UserProfile).where(UserProfile.user_id == user_id)
        profile = session.exec(statement).first()
        if not profile:
            return {}
        data = profile.__dict__.copy()
        # Remove internal SQLAlchemy properties
        data.pop("_sa_instance_state", None)
        return data

    def load_user_documents(self, session: Session, user_id: int) -> List[Document]:
        """Fetch list of user uploaded files."""
        statement = select(Document).where(Document.user_id == user_id)
        return session.exec(statement).all()

    def load_saved_relations(self, session: Session, user_id: int) -> List[UserScheme]:
        """Fetch scheme interaction logs for user."""
        statement = select(UserScheme).where(UserScheme.user_id == user_id)
        return session.exec(statement).all()
