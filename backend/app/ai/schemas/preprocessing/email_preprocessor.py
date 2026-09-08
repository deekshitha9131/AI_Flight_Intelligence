import re
from html.parser import HTMLParser

from app.ai.schemas.preprocessing import PreprocessedEmail
from app.core.constants import AI_PREPROCESSING_MAX_BODY_CHARACTERS
from app.domain.entities.email import Email

_REPLY_HEADER_PATTERN = re.compile(r"^\s*On .{0,300}?\bwrote:\s*$", re.IGNORECASE)
_ORIGINAL_MESSAGE_PATTERN = re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$", re.IGNORECASE)

_SIGNATURE_DELIMITER_PATTERN = re.compile(r"^--\s*$")

_BLOCK_TAGS = frozenset(
    {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}
)


class _HTMLTextExtractor(HTMLParser):

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._chunks.append(data)

    def get_text(self) -> str:
        return "".join(self._chunks)


def _html_to_text(html_content: str) -> str:
    """Strip HTML markup down to its readable text content."""
    extractor = _HTMLTextExtractor()
    extractor.feed(html_content)
    extractor.close()
    return extractor.get_text()


def _strip_quoted_reply(text: str) -> str:

    lines = text.split("\n")

    for i, line in enumerate(lines):
        if _REPLY_HEADER_PATTERN.match(line) or _ORIGINAL_MESSAGE_PATTERN.match(line):
            return "\n".join(lines[:i]).rstrip()

    cutoff = len(lines)
    while cutoff > 0 and (
        lines[cutoff - 1].strip() == "" or lines[cutoff - 1].lstrip().startswith(">")
    ):
        cutoff -= 1

    trailing_block = lines[cutoff:]
    if cutoff > 0 and any(line.lstrip().startswith(">") for line in trailing_block):
        return "\n".join(lines[:cutoff]).rstrip()

    return text


def _strip_signature(text: str) -> str:
    """Truncate at the standard "--" signature delimiter, if present."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if _SIGNATURE_DELIMITER_PATTERN.match(line):
            return "\n".join(lines[:i]).rstrip()
    return text


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _select_body(email: Email) -> str:
    """Prefer body_text; fall back to an HTML-derived text conversion
    of body_html; fall back to an empty string if neither is usable."""
    if email.body_text and email.body_text.strip():
        return email.body_text
    if email.body_html and email.body_html.strip():
        return _html_to_text(email.body_html)
    return ""


class EmailPreprocessor:
    def preprocess(self, email: Email) -> PreprocessedEmail:
        body = _select_body(email)
        body = _strip_quoted_reply(body)
        body = _strip_signature(body)
        body = _normalize_whitespace(body)

        truncated = False
        if len(body) > AI_PREPROCESSING_MAX_BODY_CHARACTERS:
            keep = AI_PREPROCESSING_MAX_BODY_CHARACTERS - 3  # room for the "..." marker
            body = body[:keep].rstrip() + "..."
            truncated = True

        return PreprocessedEmail(
            sender=email.sender,
            recipients=list(email.recipients),
            subject=email.subject,
            body=body,
            truncated=truncated,
        )
