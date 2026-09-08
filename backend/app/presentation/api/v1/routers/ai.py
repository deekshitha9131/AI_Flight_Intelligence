from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.schemas.ai_understanding import AIUnderstandingResult
from app.ai.services.understanding_service import AIUnderstandingService
from app.application.services.email_service import EmailService
from app.core.config import Settings
from app.core.constants import OpenAPITags
from app.core.di_container import (
    CurrentUser,
    get_email_ai_understanding_repository,
    get_email_service,
    get_llm_provider,
    get_settings_dependency,
    get_understanding_service,
)
from app.infrastructure.database.repositories.email_ai_understanding_repository import (
    EmailAIUnderstandingRepository,
)

router = APIRouter(prefix="/emails", tags=[OpenAPITags.AI_UNDERSTANDING])

EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
UnderstandingServiceDep = Annotated[AIUnderstandingService, Depends(get_understanding_service)]
AIRepositoryDep = Annotated[
    EmailAIUnderstandingRepository, Depends(get_email_ai_understanding_repository)
]
SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]


@router.post(
    "/{email_id}/analyze",
    summary="Analyze an email with AI",
    response_model=AIUnderstandingResult,
)
async def analyze_email(
    current_user: CurrentUser,
    email_id: UUID,
    email_service: EmailServiceDep,
    understanding_service: UnderstandingServiceDep,
    ai_repository: AIRepositoryDep,
) -> AIUnderstandingResult:
    email = await email_service.get_email(current_user, email_id)
    result = await understanding_service.analyze_email(email)
    await ai_repository.upsert(email.id, result)
    return result


@router.post(
    "/generate",
    summary="Generate email content from prompt",
)
async def generate_email_content(
    current_user: CurrentUser,
    settings: SettingsDep,
    to: str = "",
    subject: str = "",
    body: str = "",
    instructions: str = "",
) -> dict[str, str]:
    llm_provider = get_llm_provider(settings)
    generated_text = await llm_provider.generate_text(
        system_prompt="You are a professional email writing assistant",
        user_prompt=(
            f"Generate a professional email. To: {to}. Subject: {subject}. "
            f"Body: {body}. Instructions: {instructions}"
        ),
        model=settings.llm_drafting_model,
    )
    lines = generated_text.strip().splitlines()
    return {
        "subject": lines[0].strip() if lines else "",
        "body": "\n".join(lines[1:]).strip() if len(lines) > 1 else "",
    }