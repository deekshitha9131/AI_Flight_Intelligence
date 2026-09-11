from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.assistant import AssistantChatRequest, AssistantResponse
from app.services.assistant import AssistantService
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assistant",
    tags=["assistant"],
    responses={404: {"description": "Not found"}},
)

# We will create the assistant service per request to have access to the db session
# Alternatively, we can modify the AssistantService to take db in the method.
# We'll change the AssistantService to be instantiated with db.

@router.post("/chat", response_model=AssistantResponse)
async def assistant_chat_endpoint(
    chat_request: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main endpoint for conversational flight assistant.
    Processes natural language requests and returns flight information or clarification questions.
    """
    try:
        # Create assistant service instance with db session
        assistant_service = AssistantService(db)
        # Process the user message through the assistant service
        result = await assistant_service.process_message(
            user_input=chat_request.message,
            conversation_id=chat_request.conversation_id,
            user_id=str(current_user.id),
            db=db
        )

        return AssistantResponse(**result)

    except Exception as e:
        logger.error(f"Assistant endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assistant service unavailable"
        )