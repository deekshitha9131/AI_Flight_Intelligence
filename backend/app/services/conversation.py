from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.models.conversation import Conversation
from app.models.message import Message
from typing import Optional, List
from sqlalchemy.orm import Session

class ConversationService:
    def __init__(self, db: Session):
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)
        self.db = db

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> Conversation:
        return self.conversation_repo.create(user_id, title)

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        return self.conversation_repo.get_for_user(conversation_id, user_id)

    def list_conversations(self, user_id: str, limit: int = 50) -> List[Conversation]:
        return self.conversation_repo.list_for_user(user_id, limit)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        return self.conversation_repo.delete_for_user(conversation_id, user_id)

    def add_user_message(self, conversation_id: str, content: str) -> Message:
        message = self.message_repo.create(conversation_id, "user", content)
        self.update_conversation_timestamp(conversation_id)
        return message

    def add_assistant_message(self, conversation_id: str, content: str) -> Message:
        message = self.message_repo.create(conversation_id, "assistant", content)
        self.update_conversation_timestamp(conversation_id)
        return message

    def get_conversation_messages(self, conversation_id: str, limit: int = 100) -> List[Message]:
        return self.message_repo.list_for_conversation(conversation_id, limit)

    def update_conversation_timestamp(self, conversation_id: str) -> None:
        self.conversation_repo.update_timestamp(conversation_id)
