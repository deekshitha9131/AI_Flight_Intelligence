from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.services.conversation import ConversationService
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationListResponse, ConversationWithMessagesResponse, MessageResponse
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation for the current user.
    """
    try:
        conversation_service = ConversationService(db)
        conversation = conversation_service.create_conversation(
            user_id=str(current_user.id)
        )
        return ConversationResponse.model_validate(conversation)
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create conversation"
        )

@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all conversations for the current user, sorted by updated_at descending.
    """
    try:
        conversation_service = ConversationService(db)
        conversations = conversation_service.list_conversations(
            user_id=str(current_user.id)
        )
        return ConversationListResponse(
            conversations=[ConversationResponse.model_validate(c) for c in conversations]
        )
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve conversations"
        )

@router.get("/{conversation_id}", response_model=ConversationWithMessagesResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation by ID for the current user.
    Returns the conversation and its messages.
    """
    try:
        conversation_service = ConversationService(db)
        conversation = conversation_service.get_conversation(
            conversation_id, str(current_user.id)
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        # Get messages for the conversation
        messages = conversation_service.get_conversation_messages(
            conversation.id
        )
        # Convert messages to MessageResponse objects
        message_responses = [MessageResponse.model_validate(m) for m in messages]
        # Build the response
        response = ConversationWithMessagesResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve conversation"
        )

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation for the current user.
    """
    try:
        conversation_service = ConversationService(db)
        deleted = conversation_service.delete_conversation(
            conversation_id, str(current_user.id)
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete conversation"
        )