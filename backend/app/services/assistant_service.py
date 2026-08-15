from __future__ import annotations

import logging
import math
import time
from uuid import UUID

from app.ai.llm_provider import LLMProvider, get_system_prompt
from app.exceptions.base import ExternalAPIException, NotFoundException
from app.repositories.chat_repository import ChatRepository
from app.schemas.assistant import (
    ChatMessageItem,
    ChatResponse,
    ChatResponseData,
    ConversationDetailResponse,
    ConversationItem,
    ConversationListResponse,
    ConversationWithMessages,
    DeleteConversationResponse,
)

logger = logging.getLogger(__name__)

# Maximum number of previous messages sent to the LLM for context
_CONTEXT_WINDOW = 10


class AssistantService:
    """Business logic for the AI travel assistant.

    Responsibilities
    ----------------
    - Create / continue conversation threads.
    - Build the message history context window for the LLM.
    - Persist user and assistant messages.
    - Map repository models to clean Pydantic schemas.
    """

    def __init__(
        self,
        chat_repo: ChatRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._chat_repo = chat_repo
        self._llm = llm_provider

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        *,
        user_id: UUID,
        message: str,
        conversation_id: UUID | None,
    ) -> ChatResponse:
        """Process a user message and return the assistant reply."""
        # Resolve or create conversation
        t0 = time.monotonic()
        logger.info("[STEP 2] RESOLVING CONVERSATION START | conv_id=%s", conversation_id)
        if conversation_id is not None:
            conversation = self._chat_repo.get_conversation(
                conversation_id=conversation_id, user_id=user_id
            )
            if conversation is None:
                raise NotFoundException(message="Conversation not found.")
        else:
            # Auto-title from first 60 chars of the first message
            title = message[:60].strip() or "New Conversation"
            conversation = self._chat_repo.create_conversation(
                user_id=user_id, title=title
            )
        logger.info("[STEP 2] RESOLVING CONVERSATION COMPLETED | elapsed=%.2fms", (time.monotonic() - t0) * 1000)

        # Persist user message
        t1 = time.monotonic()
        logger.info("[STEP 3] PERSIST USER MESSAGE START")
        self._chat_repo.add_message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        logger.info("[STEP 3] PERSIST USER MESSAGE COMPLETED | elapsed=%.2fms", (time.monotonic() - t1) * 1000)

        # Build context window for LLM
        t2 = time.monotonic()
        logger.info("[STEP 4] BUILDING LLM CONTEXT START")
        history = self._chat_repo.get_messages(
            conversation_id=conversation.id, limit=_CONTEXT_WINDOW + 1
        )
        llm_messages = [{"role": "system", "content": get_system_prompt()}]
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})
        logger.info("[STEP 4] BUILDING LLM CONTEXT COMPLETED | msg_count=%d elapsed=%.2fms", len(llm_messages), (time.monotonic() - t2) * 1000)

        # Call LLM
        t3 = time.monotonic()
        logger.info("[STEP 5] CALLING LLM PROVIDER START | provider=%s", type(self._llm).__name__)
        try:
            reply, tokens = await self._llm.complete(messages=llm_messages)
            logger.info("[STEP 6] LLM CALL COMPLETED | tokens=%s elapsed=%.2fms", tokens, (time.monotonic() - t3) * 1000)
        except Exception as exc:
            logger.error("[STEP 6 ERROR] LLM CALL FAILED after %.2fms | error: %s", (time.monotonic() - t3) * 1000, exc, exc_info=True)
            raise ExternalAPIException(
                message=f"AI Assistant service error: {exc}",
                details={"error_class": exc.__class__.__name__},
            ) from exc

        # Persist assistant reply
        t4 = time.monotonic()
        logger.info("[STEP 8] DB PERSIST ASSISTANT REPLY START")
        self._chat_repo.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=reply,
            tokens_used=tokens,
        )
        self._chat_repo.touch_conversation(conversation_id=conversation.id)
        logger.info("[STEP 8] DB PERSIST ASSISTANT REPLY COMPLETED | elapsed=%.2fms", (time.monotonic() - t4) * 1000)

        logger.info(
            "AssistantService.chat | user=%s conv=%s tokens=%s",
            user_id,
            conversation.id,
            tokens,
        )

        return ChatResponse(
            success=True,
            message="Reply generated successfully.",
            data=ChatResponseData(
                conversation_id=conversation.id,
                reply=reply,
                tokens_used=tokens,
            ),
        )

    # ------------------------------------------------------------------
    # Conversation management
    # ------------------------------------------------------------------

    def list_conversations(
        self,
        *,
        user_id: UUID,
        page: int,
        page_size: int,
    ) -> ConversationListResponse:
        """Return paginated conversation list for the user."""
        page = max(1, page)
        page_size = max(1, min(page_size, 50))
        offset = (page - 1) * page_size

        records, total = self._chat_repo.list_conversations(
            user_id=user_id, offset=offset, limit=page_size
        )

        items = [
            ConversationItem(
                id=c.id,
                title=c.title,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=self._chat_repo.count_messages(conversation_id=c.id),
            )
            for c in records
        ]

        return ConversationListResponse(
            success=True,
            message="Conversations retrieved successfully.",
            data=items,
            count=total,
        )

    def get_conversation(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
    ) -> ConversationDetailResponse:
        """Return a conversation with its full message history."""
        conversation = self._chat_repo.get_conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        if conversation is None:
            raise NotFoundException(message="Conversation not found.")

        messages = self._chat_repo.get_messages(
            conversation_id=conversation_id, limit=200
        )

        return ConversationDetailResponse(
            success=True,
            message="Conversation retrieved successfully.",
            data=ConversationWithMessages(
                id=conversation.id,
                title=conversation.title,
                is_active=conversation.is_active,
                created_at=conversation.created_at,
                messages=[
                    ChatMessageItem(
                        id=m.id,
                        role=m.role,
                        content=m.content,
                        created_at=m.created_at,
                    )
                    for m in messages
                ],
            ),
        )

    def delete_conversation(
        self,
        *,
        conversation_id: UUID,
        user_id: UUID,
    ) -> DeleteConversationResponse:
        """Delete a conversation and all its messages."""
        deleted = self._chat_repo.delete_conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        if not deleted:
            raise NotFoundException(message="Conversation not found.")

        logger.info(
            "AssistantService.delete_conversation | user=%s conv=%s",
            user_id,
            conversation_id,
        )

        return DeleteConversationResponse(
            success=True,
            message="Conversation deleted successfully.",
        )
