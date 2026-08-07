"""Gmail message parser.

Converts a raw Gmail API message object (the dict returned by
GmailClient.get_message, app/infrastructure/gmail/client.py) into a
ParsedEmail (app/application/dto/gmail.py). This module is a pure
transformation: no Gmail API calls, no database access, no repository
calls — see the module docstring on GmailClient for why that split
matters, and the same reasoning applies here symmetrically. EmailParser
never talks to Gmail; GmailClient never parses a payload; only
GmailService (a later task) is allowed to know both exist.

Gmail's MIME structure is a tree: a message has a top-level `payload`,
which either *is* a leaf body (a simple non-multipart message) or has
a `parts` list of child parts, each of which may itself be multipart
(e.g. `multipart/alternative` nested inside `multipart/mixed` — the
common shape for "a plain+HTML reply with one attachment"). `_walk_part`
recurses that tree once, collecting plain text, HTML, and attachment
metadata as it goes, so the public `parse_message` never has to special-
case "simple" vs "multipart" messages itself.
"""

import base64
import binascii
from datetime import UTC, datetime
from email.utils import getaddresses
from typing import Any

from app.application.dto.gmail import ParsedAttachment, ParsedEmail
from app.domain.exceptions.gmail import GmailParseError

_MIME_TEXT_PLAIN = "text/plain"
_MIME_TEXT_HTML = "text/html"


def _decode_base64url(data: str) -> bytes:
    """Decode Gmail's Base64URL body encoding.

    Gmail omits trailing `=` padding (per the URL-safe Base64 variant
    it uses throughout the API), which `base64.urlsafe_b64decode`
    requires — so padding is restored before decoding. `binascii.Error`
    (raised on genuinely invalid Base64, not just missing padding) is
    translated into GmailParseError here rather than left to bubble up
    as a raw library exception the caller wouldn't recognize.
    """
    padding_needed = -len(data) % 4
    try:
        return base64.urlsafe_b64decode(data + "=" * padding_needed)
    except (binascii.Error, ValueError) as exc:
        raise GmailParseError("Failed to decode Base64URL message body data.") from exc


def _decode_body_text(data: str) -> str:
    """Decode a body part's raw bytes as UTF-8 text.

    `errors="replace"` rather than a strict decode: a single
    mis-encoded byte in one email body must not fail parsing of an
    otherwise-valid message — Gmail's own encoding detection is not
    perfect for every sender in the wild, and a best-effort decode
    (with the standard U+FFFD replacement character marking any bad
    byte) is the correct trade-off for an email client, not a hard
    failure.
    """
    return _decode_base64url(data).decode("utf-8", errors="replace")


def _headers_map(payload: dict[str, Any]) -> dict[str, str]:
    """Build a case-insensitive header lookup from Gmail's header list shape.

    Gmail returns headers as `[{"name": "Subject", "value": "..."}]`,
    not a dict — and header names are case-insensitive per RFC 5322
    (a sender might send `from` instead of `From`). Normalizing to
    lowercase keys once here means every other function in this module
    can do a plain, correct lookup.
    """
    return {
        header["name"].lower(): header.get("value", "")
        for header in payload.get("headers", [])
        if "name" in header
    }


def _get_header(headers: dict[str, str], name: str) -> str | None:
    value = headers.get(name.lower())
    return value if value else None


def _parse_address_list(header_value: str | None) -> list[str]:
    """Extract bare email addresses from a To/Cc/Bcc header value.

    `email.utils.getaddresses` (stdlib) correctly handles comma-
    separated, display-name-quoted address lists (e.g.
    `"Doe, Jane" <jane@example.com>, bob@example.com`) without this
    module needing its own RFC 5322 address-list parser. Only the
    address half of each `(display_name, address)` pair is kept —
    display names are not part of the `emails` schema (Doc 2 §5:
    `recipient_emails TEXT[]`), and empty/unparseable entries are
    dropped rather than kept as blank strings.
    """
    if not header_value:
        return []
    return [address for _display_name, address in getaddresses([header_value]) if address]


def _parse_sender(header_value: str | None) -> str:
    """Extract the bare sender address from a From header value.

    A message with no usable From header can't be attributed to
    anyone — that's a malformed payload for this application's
    purposes, not a message with an empty sender.
    """
    addresses = _parse_address_list(header_value)
    if not addresses:
        raise GmailParseError("Gmail message is missing a usable From header.")
    return addresses[0]


def _parse_internal_date(raw_message: dict[str, Any]) -> datetime:
    """Parse Gmail's `internalDate` (epoch milliseconds, as a string) into
    a timezone-aware UTC datetime. Required — `emails.received_at` is
    NOT NULL per the schema (Doc 2 §5), so a message without a usable
    internal date cannot be represented at all."""
    raw_value = raw_message.get("internalDate")
    if raw_value is None:
        raise GmailParseError("Gmail message is missing internalDate.")
    try:
        epoch_ms = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise GmailParseError(f"Gmail message has a non-numeric internalDate: {raw_value!r}") from exc
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)


def _is_attachment_part(part: dict[str, Any]) -> bool:
    """A part is treated as an attachment if it carries a filename.

    This matches Gmail API's own convention: an inline image or a true
    attachment both surface as a part with a non-empty `filename` and
    an `attachmentId` in `body` (the raw bytes are fetched separately
    via `messages.attachments.get`, out of scope for this task — see
    GmailClient's docstring). A body part (plain text or HTML) never
    carries a filename.
    """
    return bool(part.get("filename"))


def _walk_part(
    part: dict[str, Any],
    *,
    plain_text_chunks: list[str],
    html_chunks: list[str],
    attachments: list[ParsedAttachment],
) -> None:
    """Recursively walk one MIME part (and its children, if any),
    accumulating plain text, HTML, and attachment metadata into the
    caller-supplied lists.

    Accumulating rather than returning-and-merging keeps this function
    simple under recursion — a multipart message can legally contain
    more than one text/plain part (rare, but the MIME spec allows it),
    and concatenating every chunk found is the correct, lossless
    behavior rather than silently keeping only the first or last.
    """
    mime_type = part.get("mimeType", "")
    body = part.get("body", {}) or {}

    if _is_attachment_part(part):
        attachment_id = body.get("attachmentId")
        if attachment_id is not None:
            attachments.append(
                ParsedAttachment(
                    attachment_id=attachment_id,
                    filename=part["filename"],
                    mime_type=mime_type or "application/octet-stream",
                    size=int(body.get("size", 0)),
                )
            )
        # An attachment part is a leaf — it never has meaningful nested
        # `parts` of its own — so no need to recurse further here.
        return

    data = body.get("data")
    if mime_type == _MIME_TEXT_PLAIN and data:
        plain_text_chunks.append(_decode_body_text(data))
    elif mime_type == _MIME_TEXT_HTML and data:
        html_chunks.append(_decode_body_text(data))

    for child_part in part.get("parts", []) or []:
        _walk_part(
            child_part,
            plain_text_chunks=plain_text_chunks,
            html_chunks=html_chunks,
            attachments=attachments,
        )


class EmailParser:
    """Stateless converter from a raw Gmail message dict to a ParsedEmail.

    Stateless by design (no `__init__`, every method usable directly
    off the class or an instance) — there is nothing to configure or
    hold between calls, matching how a pure transformation function
    should be shaped. Kept as a class rather than a bare module
    function only for import-site consistency with GmailClient
    (`EmailParser().parse_message(...)` reads the same way
    `GmailClient(...).get_message(...)` does) — a later task's service
    layer can hold one instance the same way it holds one client.
    """

    def parse_message(self, raw_message: dict[str, Any]) -> ParsedEmail:
        """Parse one Gmail API message object (as returned by
        `GmailClient.get_message(..., format="full")`) into a ParsedEmail.

        Raises GmailParseError if the payload is missing a field this
        application cannot function without (message ID, thread ID,
        a usable From header, or internalDate), or if a body part's
        Base64URL data is invalid.
        """
        message_id = raw_message.get("id")
        thread_id = raw_message.get("threadId")
        payload = raw_message.get("payload")

        if not message_id:
            raise GmailParseError("Gmail message is missing its id.")
        if not thread_id:
            raise GmailParseError("Gmail message is missing its threadId.")
        if not payload:
            raise GmailParseError("Gmail message is missing its payload.")

        headers = _headers_map(payload)

        plain_text_chunks: list[str] = []
        html_chunks: list[str] = []
        attachments: list[ParsedAttachment] = []
        _walk_part(
            payload,
            plain_text_chunks=plain_text_chunks,
            html_chunks=html_chunks,
            attachments=attachments,
        )

        return ParsedEmail(
            gmail_message_id=message_id,
            gmail_thread_id=thread_id,
            subject=_get_header(headers, "Subject"),
            sender=_parse_sender(_get_header(headers, "From")),
            recipients=_parse_address_list(_get_header(headers, "To")),
            cc=_parse_address_list(_get_header(headers, "Cc")),
            bcc=_parse_address_list(_get_header(headers, "Bcc")),
            snippet=raw_message.get("snippet", ""),
            internal_date=_parse_internal_date(raw_message),
            label_ids=list(raw_message.get("labelIds", [])),
            body_text="\n".join(plain_text_chunks) if plain_text_chunks else None,
            body_html="\n".join(html_chunks) if html_chunks else None,
            attachments=attachments,
        )   