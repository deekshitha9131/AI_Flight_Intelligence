from sqlalchemy.orm import Session
from app.models.message import Message
from typing import List

class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, conversation_id: str, role: str, content: str) -> Message:
        message = Message(
            id=str(__import__('uuid').uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_for_conversation(self, conversation_id: str, limit: int = 100) -> List[Message]:
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).limit(limit).all()