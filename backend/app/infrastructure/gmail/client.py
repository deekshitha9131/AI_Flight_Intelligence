"""Gmail API client.

The single gateway for all Gmail API communication — every read/send
operation the rest of the application needs from Gmail flows through
this class. Nothing here touches the database or implements a
sync/send *workflow*; those are service-layer concerns (see
GmailService). This module's job is: "given a user's OAuth tokens, let
the caller talk to the Gmail API and get predictable results back" —
extended in Task 3.5 to also cover building and sending a MIME email,
since the doc's own architecture section places "convert to raw
MIME, Base64URL encode, call users.messages.send" here, not in the
service.

Deliberately built on `google-api-python-client` (already a project
dependency), not raw httpx — see this module's original docstring
(unchanged) for why. It is synchronous end-to-end, so every call here
is bridged onto a worker thread via `asyncio.to_thread` rather than
blocking the event loop.
"""

import asyncio
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable, TypeVar

import structlog
from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from app.core.config import Settings
from app.core.constants import GOOGLE_TOKEN_ENDPOINT
from app.domain.entities.oauth_token import OAuthToken
from app.domain.exceptions.gmail import GmailAPIError, GmailAuthenticationError

logger = structlog.get_logger(__name__)

T = TypeVar("T")

_GMAIL_SERVICE_NAME = "gmail"
_GMAIL_SERVICE_VERSION = "v1"
_DEFAULT_MAX_RESULTS = 100

# HTTP statuses Gmail returns when the caller's credentials are the
# problem (expired/revoked/insufficient scope) — worth distinguishing
# from every other Gmail API failure so the caller can tell "the user
# needs to reconnect Gmail" apart from "Gmail had a bad day."
_AUTH_FAILURE_STATUSES = frozenset({401, 403})


class GmailClient:
    """Wraps the Gmail API operations the rest of the application needs.

    Constructed per-use (one instance per request/task, holding exactly
    one user's tokens) — never safe to share one instance across
    different users' requests.
    """

    def __init__(self, *, oauth_token: OAuthToken, settings: Settings) -> None:
        self._oauth_token = oauth_token
        self._settings = settings
        self._service: Resource | None = None

    def _build_credentials(self) -> Credentials:
        """Build google-auth Credentials from the stored (decrypted) OAuth tokens."""
        return Credentials(
            token=self._oauth_token.access_token,
            refresh_token=self._oauth_token.refresh_token,
            token_uri=GOOGLE_TOKEN_ENDPOINT,
            client_id=self._settings.google_client_id,
            client_secret=self._settings.google_client_secret,
            scopes=self._oauth_token.granted_scopes,
        )

    def _get_service(self) -> Resource:
        """Return the memoized Gmail API `Resource`, building it on first use."""
        if self._service is None:
            try:
                credentials = self._build_credentials()
                self._service = build(
                    _GMAIL_SERVICE_NAME,
                    _GMAIL_SERVICE_VERSION,
                    credentials=credentials,
                    cache_discovery=False,
                )
            except GoogleAuthError as exc:
                raise GmailAuthenticationError(
                    "Failed to build an authenticated Gmail API client from "
                    "the stored OAuth tokens."
                ) from exc
        return self._service

    async def _execute(self, operation: Callable[[Resource], T]) -> T:
        """Run a synchronous googleapiclient call off the event loop and
        translate its errors into this project's domain exceptions."""
        service = self._get_service()
        try:
            return await asyncio.to_thread(operation, service)
        except HttpError as exc:
            status = exc.resp.status if exc.resp is not None else None
            if status in _AUTH_FAILURE_STATUSES:
                raise GmailAuthenticationError(
                    "Gmail rejected the request as unauthenticated or "
                    "unauthorized — the stored OAuth tokens may be expired "
                    "or revoked."
                ) from exc
            raise GmailAPIError(f"Gmail API request failed with status {status}.") from exc
        except GoogleAuthError as exc:
            raise GmailAuthenticationError(
                "Failed to authenticate with Gmail using the stored OAuth tokens."
            ) from exc

    # ------------------------------------------------------------------
    # Public Gmail API operations
    # ------------------------------------------------------------------

    async def get_profile(self) -> dict[str, Any]:
        """Return the connected Gmail account's profile."""
        return await self._execute(lambda service: service.users().getProfile(userId="me").execute())

    async def list_messages(
        self,
        *,
        query: str | None = None,
        label_ids: list[str] | None = None,
        page_token: str | None = None,
        max_results: int = _DEFAULT_MAX_RESULTS,
    ) -> dict[str, Any]:
        """List message IDs matching the given filters."""

        def _call(service: Resource) -> dict[str, Any]:
            request = service.users().messages().list(
                userId="me",
                q=query,
                labelIds=label_ids,
                pageToken=page_token,
                maxResults=max_results,
            )
            return request.execute()

        return await self._execute(_call)

    async def get_message(self, message_id: str, *, format: str = "full") -> dict[str, Any]:
        """Fetch a single message by Gmail message ID."""
        return await self._execute(
            lambda service: service.users().messages().get(userId="me", id=message_id, format=format).execute()
        )

    async def list_history(
        self, *, start_history_id: str, page_token: str | None = None
    ) -> dict[str, Any]:
        """List mailbox changes since `start_history_id`."""

        def _call(service: Resource) -> dict[str, Any]:
            request = service.users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                pageToken=page_token,
            )
            return request.execute()

        return await self._execute(_call)

    async def send_message(self, *, raw_message: str, thread_id: str | None = None) -> dict[str, Any]:
        """Send a pre-built, base64url-encoded RFC 2822 message via Gmail.

        `raw_message` must already be a complete, base64url-encoded MIME
        message. Passing `thread_id` keeps a reply attached to its
        Gmail thread instead of starting a new one. Kept as its own
        public method (not folded into `send_email` below) so a caller
        that already has a raw MIME payload from elsewhere can still
        use this client without going through MIME construction again.
        """

        def _call(service: Resource) -> dict[str, Any]:
            body: dict[str, Any] = {"raw": raw_message}
            if thread_id is not None:
                body["threadId"] = thread_id
            return service.users().messages().send(userId="me", body=body).execute()

        return await self._execute(_call)

    # ------------------------------------------------------------------
    # Task 3.5 — structured send (MIME construction + Base64URL encode)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_mime_message(
        *,
        to: list[str],
        cc: list[str],
        bcc: list[str],
        subject: str,
        body_text: str | None,
        body_html: str | None,
    ) -> MIMEMultipart | MIMEText:
        """Build an RFC 5322 MIME message from structured fields.

        Three shapes, matching what was actually provided:
        - both bodies → `multipart/alternative` with a text/plain part
          and a text/html part, letting the receiving client pick
          whichever it renders best (the standard email convention).
        - html only → a bare `text/html` message.
        - text only (or neither, though callers validate that before
          reaching this point — see GmailService.send_email and
          GmailSendRequest's schema validator) → a bare `text/plain`
          message.

        No `From` header is set deliberately — Gmail's send API fills
        the authenticated user's own address in automatically, and
        setting a mismatched one manually is a well-known way to get a
        message silently rejected or flagged.
        """
        if body_text and body_html:
            message: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
            message.attach(MIMEText(body_text, "plain", "utf-8"))
            message.attach(MIMEText(body_html, "html", "utf-8"))
        elif body_html:
            message = MIMEText(body_html, "html", "utf-8")
        else:
            message = MIMEText(body_text or "", "plain", "utf-8")

        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)
        message["Subject"] = subject
        return message

    @staticmethod
    def _encode_base64url(message: MIMEMultipart | MIMEText) -> str:
        """Base64URL-encode a MIME message's full byte serialization —
        Gmail's `users.messages.send` requires the `raw` field in
        exactly this encoding."""
        return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Build a MIME email from structured fields and send it via Gmail.

        This is the method GmailService calls for Task 3.5's /gmail/send
        workflow — `send_message` above remains available separately for
        any future caller that already has a raw payload. Passing
        `thread_id` sends as a reply within that Gmail thread; omitting
        it starts a new conversation.
        """
        message = self._build_mime_message(
            to=to, cc=cc or [], bcc=bcc or [], subject=subject, body_text=body_text, body_html=body_html
        )
        raw_message = self._encode_base64url(message)
        return await self.send_message(raw_message=raw_message, thread_id=thread_id)