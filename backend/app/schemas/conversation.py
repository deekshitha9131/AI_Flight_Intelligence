from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ConversationCreate(BaseModel):
    # No fields needed for creation, but we can add title if desired
    title: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime

    model_config = {'from_attributes': True}

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]

    model_config = {'from_attributes': True}

class ConversationWithMessagesResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]

    model_config = {'from_attributes': True}
