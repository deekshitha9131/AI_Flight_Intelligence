"""Threads router.

Implements the two read-only thread endpoints from Task 4.4: listing
(with per-thread email_count) and detail (thread + all its emails,
chronological order). Every endpoint delegates to ThreadService — this
file never touches ThreadRepository, EmailRepository, or SQLAlchemy
directly, same division of responsibility as every other router in
this project.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.application.services.thread_service import ThreadService
from app.core.constants import OpenAPITags
from app.core.di_container import CurrentUser, get_thread_service
from app.presentation.api.v1.schemas.email import EmailDetail
from app.presentation.api.v1.schemas.thread import (
    ThreadDetailResponse,
    ThreadListResponse,
    ThreadQueryParams,
    ThreadSummarySchema,
)

router = APIRouter(prefix="/threads", tags=[OpenAPITags.THREADS])

ThreadServiceDep = Annotated[ThreadService, Depends(get_thread_service)]


@router.get(
    "",
    summary="List the authenticated user's threads",
    description="Returns a paginated, sorted (by recent activity) list "
    "of the authenticated user's threads, each with an email_count. "
    "Does not load full email bodies.",
    response_model=ThreadListResponse,
)
async def list_threads(
    current_user: CurrentUser,
    thread_service: ThreadServiceDep,
    params: Annotated[ThreadQueryParams, Depends()],
) -> ThreadListResponse:
    items, total = await thread_service.list_threads(
        current_user, page=params.page, page_size=params.page_size, sort=params.sort
    )
    return ThreadListResponse(
        items=[ThreadSummarySchema.model_validate(item) for item in items],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get(
    "/{thread_id}",
    summary="Get one thread with all its emails",
    description="Returns thread metadata plus every email belonging to "
    "it, in chronological order. Returns 404 if the thread does not "
    "exist or belongs to another user — the two cases are "
    "indistinguishable in the response, by design.",
    response_model=ThreadDetailResponse,
)
async def get_thread(
    current_user: CurrentUser,
    thread_service: ThreadServiceDep,
    thread_id: UUID,
) -> ThreadDetailResponse:
    thread, emails = await thread_service.get_thread(current_user, thread_id)
    return ThreadDetailResponse(
        id=thread.id,
        gmail_thread_id=thread.gmail_thread_id,
        subject=thread.subject,
        snippet=thread.snippet,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        emails=[EmailDetail.model_validate(email) for email in emails],
    )
