from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.conversation import Conversation
from app.models.message import Message
from typing import Optional, List

class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, title: Optional[str] = None) -> Conversation:
        conversation = Conversation(
            id=str(__import__('uuid').uuid4()),
            user_id=user_id,
            title=title or "Flight Search Conversation",
            updated_at=func.now()
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_for_user(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

    def list_for_user(self, user_id: str, limit: int = 50) -> List[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).limit(limit).all()

    def delete_for_user(self, conversation_id: str, user_id: str) -> bool:
        conversation = self.get_for_user(conversation_id, user_id)
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False

    def update_timestamp(self, conversation_id: str) -> None:
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = func.now()
            self.db.commit()
