from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /api/v1/assistant/chat."""

    message: str = Field(
        ..., min_length=1, max_length=2000, description="User message to the assistant."
    )
    conversation_id: UUID | None = Field(
        None,
        description="Existing conversation ID to continue. Omit to start a new conversation.",
    )


class ChatMessageItem(BaseModel):
    """A single message in a conversation thread."""

    id: UUID
    role: str = Field(..., description="'user' or 'assistant'.")
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationItem(BaseModel):
    """Summary of a conversation thread."""

    id: UUID
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(
        0, description="Number of messages in this conversation."
    )

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """Response for POST /api/v1/assistant/chat."""

    success: bool
    message: str
    data: ChatResponseData


class ChatResponseData(BaseModel):
    """Payload returned after a chat turn."""

    conversation_id: UUID
    reply: str = Field(..., description="Assistant reply text.")
    tokens_used: int | None = Field(
        None, description="LLM tokens consumed, if available."
    )


class ConversationListResponse(BaseModel):
    """Response for GET /api/v1/assistant/conversations."""

    success: bool
    message: str
    data: list[ConversationItem]
    count: int


class ConversationDetailResponse(BaseModel):
    """Response for GET /api/v1/assistant/conversations/{id}."""

    success: bool
    message: str
    data: ConversationWithMessages


class ConversationWithMessages(BaseModel):
    """A conversation with its full message history."""

    id: UUID
    title: str
    is_active: bool
    created_at: datetime
    messages: list[ChatMessageItem]


class DeleteConversationResponse(BaseModel):
    """Response after deleting a conversation."""

    success: bool
    message: str


# Rebuild forward references
ChatResponse.model_rebuild()
ConversationDetailResponse.model_rebuild()
