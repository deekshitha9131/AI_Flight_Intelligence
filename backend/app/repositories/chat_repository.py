from __future__ import annotations

import logging
from uuid import UUID

from app.models.chat import ChatConversation, ChatMessage
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository layer for AI assistant conversation persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_conversation(
        self, *, user_id: UUID, title: str = "New Conversation"
    ) -> ChatConversation:
        """Create a new conversation thread."""
        record = ChatConversation(user_id=user_id, title=title)
        self._db.add(record)
        self._db.flush()
        logger.info(
            "ChatRepository.create_conversation | user=%s id=%s", user_id, record.id
        )
        return record

    def get_conversation(
        self, *, conversation_id: UUID, user_id: UUID
    ) -> ChatConversation | None:
        """Return a conversation owned by the user, or None."""
        return self._db.scalar(
            select(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id,
            )
        )

    def list_conversations(
        self,
        *,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ChatConversation], int]:
        """Return paginated conversations for a user, newest-first."""
        base_filter = ChatConversation.user_id == user_id

        total: int = (
            self._db.scalar(
                select(func.count()).select_from(ChatConversation).where(base_filter)
            )
            or 0
        )

        records = list(
            self._db.scalars(
                select(ChatConversation)
                .where(base_filter)
                .order_by(ChatConversation.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return records, total

    def update_conversation_title(self, *, conversation_id: UUID, title: str) -> None:
        """Update the title of a conversation."""
        self._db.execute(
            update(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .values(title=title)
        )
        self._db.flush()

    def touch_conversation(self, *, conversation_id: UUID) -> None:
        """Bump updated_at to now so the conversation sorts to the top."""
        from datetime import datetime, timezone

        self._db.execute(
            update(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        self._db.flush()

    def delete_conversation(self, *, conversation_id: UUID, user_id: UUID) -> bool:
        """Delete a conversation and cascade-delete its messages."""
        from sqlalchemy import delete as sa_delete

        result = self._db.execute(
            sa_delete(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id,
            )
        )
        self._db.flush()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(
        self,
        *,
        conversation_id: UUID,
        role: str,
        content: str,
        tokens_used: int | None = None,
    ) -> ChatMessage:
        """Append a message to a conversation."""
        msg = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
        )
        self._db.add(msg)
        self._db.flush()
        return msg

    def get_messages(
        self,
        *,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """Return the most recent messages in a conversation, oldest-first."""
        return list(
            self._db.scalars(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(limit)
            )
        )

    def count_messages(self, *, conversation_id: UUID) -> int:
        """Return the total number of messages in a conversation."""
        return (
            self._db.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Structured conversation context
    # ------------------------------------------------------------------

    def get_conversation_context(self, *, conversation_id: UUID) -> dict | None:
        """Load the structured flight context JSON for a conversation.

        Returns the deserialized dict, or None if no context is stored.
        """
        import json

        raw = self._db.scalar(
            select(ChatConversation.context_json).where(
                ChatConversation.id == conversation_id
            )
        )
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Failed to parse context_json for conversation %s", conversation_id
            )
            return None

    def update_conversation_context(
        self, *, conversation_id: UUID, context: dict
    ) -> None:
        """Persist the structured flight context JSON for a conversation."""
        import json

        self._db.execute(
            update(ChatConversation)
            .where(ChatConversation.id == conversation_id)
            .values(context_json=json.dumps(context, default=str))
        )
        self._db.flush()
