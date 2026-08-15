from __future__ import annotations

import logging
import time
from uuid import UUID

from app.dependencies.ai import get_assistant_service
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.assistant import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    DeleteConversationResponse,
)
from app.services.assistant_service import AssistantService
from fastapi import APIRouter, Depends, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with the AI travel assistant",
    description=(
        "Send a message to the AI travel assistant and receive a contextual reply. "
        "Omit `conversation_id` to start a new conversation; include it to continue "
        "an existing thread.\n\n"
        "The assistant can help with:\n"
        "- Flight search and booking advice\n"
        "- Fare rules and baggage policies\n"
        "- Destination recommendations\n"
        "- Price trends and booking windows\n"
        "- Travel planning\n\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
        404: {"description": "Conversation not found."},
    },
)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> ChatResponse:
    """Send a message to the AI travel assistant."""
    start_t = time.monotonic()
    logger.info("[STEP 1] ASSISTANT REQUEST RECEIVED | user_id=%s message=%s", current_user.id, payload.message)
    res = await service.chat(
        user_id=current_user.id,
        message=payload.message,
        conversation_id=payload.conversation_id,
    )
    elapsed_ms = (time.monotonic() - start_t) * 1000
    logger.info("[STEP 10] ASSISTANT RESPONSE GENERATED | total_elapsed=%.2fms", elapsed_ms)
    return res


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversations",
    description=(
        "Return a paginated list of the authenticated user's conversation threads, "
        "sorted by most recently updated.\\n\\n"
        "**Authentication required.**"
    ),
    responses={401: {"description": "Authentication required."}},
)
def list_conversations(
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(10, ge=1, le=50, description="Records per page."),
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> ConversationListResponse:
    """Return the authenticated user's paginated conversation list."""
    return service.list_conversations(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation with messages",
    description=(
        "Return a single conversation thread with its full message history.\\n\\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
        404: {"description": "Conversation not found."},
    },
)
def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> ConversationDetailResponse:
    """Return a conversation with its full message history."""
    return service.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=DeleteConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a conversation",
    description=(
        "Delete a conversation and all its messages. "
        "Users can only delete their own conversations.\\n\\n"
        "**Authentication required.**"
    ),
    responses={
        401: {"description": "Authentication required."},
        404: {"description": "Conversation not found."},
    },
)
def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> DeleteConversationResponse:
    """Delete a conversation owned by the authenticated user."""
    return service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
