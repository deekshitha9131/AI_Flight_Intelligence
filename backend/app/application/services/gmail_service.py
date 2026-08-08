from dataclasses import dataclass
from typing import Any

import structlog

from app.application.dto.gmail import (
    GmailIncrementalSyncSummary,
    GmailSendResult,
    GmailSyncSummary,
    ParsedEmail,
)
from app.core.config import Settings
from app.core.constants import GMAIL_LIST_PAGE_SIZE, MAX_MESSAGES_PER_SYNC
from app.domain.entities.user import User
from app.domain.exceptions.gmail import (
    GmailNotConnectedError,
    GmailParseError,
    GmailSyncRequiredError,
)
from app.infrastructure.database.repositories.email_repository import EmailRepository
from app.infrastructure.database.repositories.thread_repository import ThreadRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.gmail.client import GmailClient
from app.infrastructure.gmail.parser import EmailParser

logger = structlog.get_logger(__name__)

_RELEVANT_HISTORY_KEYS = ("messagesAdded", "labelsAdded", "labelsRemoved")


@dataclass
class _MessageSyncOutcome:
    skipped: bool
    thread_id: str | None
    attachments_count: int


class GmailService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        thread_repository: ThreadRepository,
        email_repository: EmailRepository,
        settings: Settings,
        parser: EmailParser | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._thread_repository = thread_repository
        self._email_repository = email_repository
        self._settings = settings
        self._parser = parser or EmailParser()

    async def _get_connected_client(self, user: User) -> GmailClient:
        oauth_token = await self._user_repository.get_oauth_tokens(user.id)
        if oauth_token is None:
            raise GmailNotConnectedError(
                "Gmail is not connected for this account. Please connect Gmail first."
            )
        return GmailClient(oauth_token=oauth_token, settings=self._settings)

    async def _fetch_parse_and_store(
        self, gmail_client: GmailClient, user: User, message_id: str
    ) -> _MessageSyncOutcome:
        """Fetch one full Gmail message, parse it, and upsert its thread
        and email records. Shared by sync_mailbox and sync_incremental."""
        raw_message = await gmail_client.get_message(message_id)

        try:
            parsed: ParsedEmail = self._parser.parse_message(raw_message)
        except GmailParseError as exc:
            logger.warning(
                "gmail_sync_skipped_unparseable_message",
                user_id=str(user.id),
                message_id=message_id,
                error=str(exc),
            )
            return _MessageSyncOutcome(skipped=True, thread_id=None, attachments_count=0)

        thread = await self._thread_repository.upsert(
            user_id=user.id,
            gmail_thread_id=parsed.gmail_thread_id,
            subject=parsed.subject,
            snippet=parsed.snippet,
            history_id=None,
        )
        await self._email_repository.upsert(thread_id=thread.id, user_id=user.id, parsed=parsed)

        return _MessageSyncOutcome(
            skipped=False, thread_id=str(thread.id), attachments_count=len(parsed.attachments)
        )

    async def sync_mailbox(self, user: User, *, page_token: str | None = None) -> GmailSyncSummary:
        gmail_client = await self._get_connected_client(user)

        threads_synced: set[str] = set()
        emails_synced = 0
        emails_skipped = 0
        attachments_found = 0
        list_response = await gmail_client.list_messages(
            page_token=page_token,
            max_results=GMAIL_LIST_PAGE_SIZE,
        )
        message_refs = list_response.get("messages") or []

        for ref in message_refs:
            outcome = await self._fetch_parse_and_store(gmail_client, user, ref["id"])

            if outcome.skipped:
                emails_skipped += 1
            else:
                emails_synced += 1
                attachments_found += outcome.attachments_count
                if outcome.thread_id is not None:
                    threads_synced.add(outcome.thread_id)

        next_page_token = list_response.get("nextPageToken")

        logger.info(
            "gmail_sync_complete",
            user_id=str(user.id),
            threads_synced=len(threads_synced),
            emails_synced=emails_synced,
            emails_skipped=emails_skipped,
            attachments_found=attachments_found,
            resumable=next_page_token is not None,
        )

        return GmailSyncSummary(
            success=True,
            threads_synced=len(threads_synced),
            emails_synced=emails_synced,
            attachments_found=attachments_found,
            emails_skipped=emails_skipped,
            next_page_token=next_page_token,
        )

    @staticmethod
    def _extract_changed_message_ids(history_records: list[dict[str, Any]]) -> list[str]:
        seen: set[str] = set()
        ordered_ids: list[str] = []
        for record in history_records:
            for key in _RELEVANT_HISTORY_KEYS:
                for entry in record.get(key, []) or []:
                    message = entry.get("message") or {}
                    message_id = message.get("id")
                    if message_id and message_id not in seen:
                        seen.add(message_id)
                        ordered_ids.append(message_id)
        return ordered_ids

    async def sync_incremental(self, user: User) -> GmailIncrementalSyncSummary:
        gmail_client = await self._get_connected_client(user)

        stored_history_id = await self._user_repository.get_gmail_history_id(user.id)
        if stored_history_id is None:
            raise GmailSyncRequiredError(
                "No prior Gmail sync found for this account. Run an initial "
                "sync (POST /gmail/sync) before requesting an incremental sync."
            )

        threads_updated: set[str] = set()
        emails_synced = 0
        emails_skipped = 0
        attachments_found = 0
        messages_processed = 0
        latest_history_id = stored_history_id
        page_token: str | None = None

        while messages_processed < MAX_MESSAGES_PER_SYNC:
            history_response = await gmail_client.list_history(
                start_history_id=stored_history_id, page_token=page_token
            )

            response_history_id = history_response.get("historyId")
            if response_history_id:
                latest_history_id = str(response_history_id)

            history_records = history_response.get("history") or []
            changed_message_ids = self._extract_changed_message_ids(history_records)

            for message_id in changed_message_ids:
                outcome = await self._fetch_parse_and_store(gmail_client, user, message_id)
                messages_processed += 1

                if outcome.skipped:
                    emails_skipped += 1
                else:
                    emails_synced += 1
                    attachments_found += outcome.attachments_count
                    if outcome.thread_id is not None:
                        threads_updated.add(outcome.thread_id)

                if messages_processed >= MAX_MESSAGES_PER_SYNC:
                    break

            page_token = history_response.get("nextPageToken")
            if page_token is None:
                break

        await self._user_repository.update_gmail_history_id(user.id, latest_history_id)

        logger.info(
            "gmail_incremental_sync_complete",
            user_id=str(user.id),
            threads_updated=len(threads_updated),
            emails_synced=emails_synced,
            emails_skipped=emails_skipped,
            attachments_found=attachments_found,
            history_id=latest_history_id,
        )

        return GmailIncrementalSyncSummary(
            success=True,
            emails_synced=emails_synced,
            threads_updated=len(threads_updated),
            attachments_found=attachments_found,
            emails_skipped=emails_skipped,
            history_id=latest_history_id,
        )

    async def send_email(
        self,
        user: User,
        *,
        to: list[str],
        subject: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        thread_id: str | None = None,
    ) -> GmailSendResult:
        gmail_client = await self._get_connected_client(user)

        response = await gmail_client.send_email(
            to=to,
            subject=subject,
            cc=cc,
            bcc=bcc,
            body_text=body_text,
            body_html=body_html,
            thread_id=thread_id,
        )

        gmail_message_id = response["id"]
        gmail_thread_id = response.get("threadId") or thread_id or ""

        logger.info(
            "gmail_email_sent",
            user_id=str(user.id),
            gmail_message_id=gmail_message_id,
            gmail_thread_id=gmail_thread_id,
            is_reply=thread_id is not None,
        )

        return GmailSendResult(
            success=True,
            gmail_message_id=gmail_message_id,
            gmail_thread_id=gmail_thread_id,
        )
