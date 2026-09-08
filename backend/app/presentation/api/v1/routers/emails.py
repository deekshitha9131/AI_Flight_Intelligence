"""Emails router.

Implements the read-only inbox endpoints: listing and detail
(Task 4.2), and search (Task 4.3). Every endpoint is served entirely
from PostgreSQL via EmailService — this file never touches
Gmail directly, only translates between HTTP concerns (query params,
path params, response schemas) and the service call.

`/search` is registered before `/{email_id}` — `email_id` is UUID-typed
so `"search"` would never actually match it, but registering the
static path first is the standard, unambiguous FastAPI convention for
a literal path segment that could otherwise sit next to a dynamic one.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.email_service import EmailService
from app.ai.rag.indexing_service import EmailIndexingService
from app.core.constants import OpenAPITags
from app.core.di_container import CurrentUser, get_email_service, get_email_indexing_service
from app.domain.entities.email import Email
from app.domain.exceptions.email import EmailNotFoundError
from app.presentation.api.v1.schemas.email import (
    EmailDetail,
    EmailListResponse,
    EmailQueryParams,
    EmailSearchQueryParams,
    EmailSummary,
)

router = APIRouter(prefix="/emails", tags=[OpenAPITags.EMAILS])

EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
EmailIndexingServiceDep = Annotated[EmailIndexingService, Depends(get_email_indexing_service)]


@router.post(
    "/{email_id}/index",
    status_code=status.HTTP_200_OK,
    summary="Index an email for RAG retrieval",
    description="Triggers the indexing pipeline for a specific email: preprocesses, chunks, generates embeddings, and stores the results in the vector database. Returns the number of chunks created. Idempotent — re-indexing replaces existing chunks.",
    response_model=int,
)
async def index_email(
    current_user: CurrentUser,
    email_id: UUID,
    email_service: EmailServiceDep,
    indexing_service: EmailIndexingServiceDep,
) -> int:
    """Index an email for RAG retrieval."""
    email = await email_service.get_email(current_user, email_id)
    chunk_count = await indexing_service.index_email(email)
    return chunk_count


@router.get(
    "/search",
    summary="Search the authenticated user's inbox",
    description="Case-insensitive text search across sender, subject, "
    "snippet, and body — scoped entirely to the authenticated user. "
    "Rejects empty or whitespace-only queries.",
    response_model=EmailListResponse,
)
async def search_emails(
    current_user: CurrentUser,
    email_service: EmailServiceDep,
    params: Annotated[EmailSearchQueryParams, Depends()],
) -> EmailListResponse:
    items, total = await email_service.search_emails(
        current_user, query=params.q, page=params.page, page_size=params.page_size
    )
    return EmailListResponse(
        items=[EmailSummary.model_validate(item) for item in items],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get(
    "",
    summary="List the authenticated user's inbox",
    description="Returns a paginated, sorted, and optionally filtered page "
    "of the authenticated user's locally stored emails. Read entirely "
    "from PostgreSQL — this endpoint never calls Gmail.",
    response_model=EmailListResponse,
)
async def list_emails(
    current_user: CurrentUser,
    email_service: EmailServiceDep,
    params: Annotated[EmailQueryParams, Depends()],
) -> EmailListResponse:
    # `unread` is the query param's natural spelling for a filter the
    # domain models as `is_read` — translated here, at the boundary,
    # rather than exposing the inverted flag name to API consumers.
    is_read = (not params.unread) if params.unread is not None else None

    items, total = await email_service.list_emails(
        current_user,
        page=params.page,
        page_size=params.page_size,
        sort=params.sort,
        is_read=is_read,
        is_starred=params.starred,
        has_attachments=params.has_attachments,
    )
    return EmailListResponse(
        items=[EmailSummary.model_validate(item) for item in items],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get(
    "/{email_id}",
    summary="Get a single email",
    description="Returns full detail for one email owned by the "
    "authenticated user. Returns 404 if the email does not exist or "
    "belongs to another user — the two cases are indistinguishable in "
    "the response, by design.",
    response_model=EmailDetail,
)
async def get_email(
    current_user: CurrentUser,
    email_service: EmailServiceDep,
    email_id: UUID,
) -> EmailDetail:
    email = await email_service.get_email(current_user, email_id)
    return EmailDetail.model_validate(email)