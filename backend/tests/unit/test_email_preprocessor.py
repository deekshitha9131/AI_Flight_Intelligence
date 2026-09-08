from datetime import UTC, datetime
from uuid import uuid4

from app.ai.preprocessing.email_preprocessor import EmailPreprocessor
from app.core.constants import AI_PREPROCESSING_MAX_BODY_CHARACTERS
from app.domain.entities.email import Email


def _email(**overrides) -> Email:
    defaults = dict(
        id=uuid4(),
        thread_id=uuid4(),
        user_id=uuid4(),
        gmail_message_id="m1",
        sender="jane@example.com",
        recipients=["bob@example.com"],
        cc=[],
        bcc=[],
        subject="Project Update",
        snippet="snippet",
        body_text=None,
        body_html=None,
        received_at=datetime.now(UTC),
        is_read=True,
        is_starred=False,
        has_attachments=False,
        label_ids=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Email(**defaults)


def _preprocessor() -> EmailPreprocessor:
    return EmailPreprocessor()


def test_plain_text_email_is_processed_correctly() -> None:
    email = _email(body_text="Hello, this is a plain text message.")

    result = _preprocessor().preprocess(email)

    assert result.body == "Hello, this is a plain text message."
    assert result.truncated is False


def test_html_only_email_is_converted_to_readable_text() -> None:
    email = _email(body_text=None, body_html="<p>Hello <b>world</b>.</p>")

    result = _preprocessor().preprocess(email)

    assert "Hello world." in result.body
    assert "<p>" not in result.body
    assert "<b>" not in result.body


def test_body_text_is_preferred_over_body_html() -> None:
    email = _email(body_text="Plain version.", body_html="<p>HTML version.</p>")

    result = _preprocessor().preprocess(email)

    assert result.body == "Plain version."
    assert "HTML version" not in result.body


def test_empty_body_is_handled_safely() -> None:
    email = _email(body_text=None, body_html=None)
    result = _preprocessor().preprocess(email)
    assert result.body == ""
    assert result.truncated is False


def test_whitespace_only_body_text_falls_back_to_html() -> None:
    email = _email(body_text="   \n  ", body_html="<p>Real content.</p>")
    result = _preprocessor().preprocess(email)
    assert "Real content." in result.body


def test_whitespace_is_normalized() -> None:
    email = _email(body_text="  Hello    world.  \n\n\n\n  Second   line.  ")
    result = _preprocessor().preprocess(email)
    assert result.body == "Hello world.\n\nSecond line."


def test_html_paragraph_breaks_produce_readable_structure() -> None:
    email = _email(body_text=None, body_html="<p>First paragraph.</p><p>Second paragraph.</p>")
    result = _preprocessor().preprocess(email)
    assert result.body == "First paragraph.\n\nSecond paragraph."


def test_html_script_and_style_content_is_excluded() -> None:
    email = _email(
        body_text=None,
        body_html="<style>.x{color:red}</style><p>Visible text.</p><script>alert('x')</script>",
    )
    result = _preprocessor().preprocess(email)
    assert result.body == "Visible text."
    assert "alert" not in result.body
    assert "color:red" not in result.body


def test_html_entities_are_decoded() -> None:
    email = _email(body_text=None, body_html="<p>Terms &amp; Conditions</p>")
    result = _preprocessor().preprocess(email)
    assert "Terms & Conditions" in result.body


def test_reply_header_marker_truncates_quoted_content() -> None:
    email = _email(
        body_text=(
            "Thanks, sounds good.\n\n"
            "On Mon, Aug 3, 2026 at 10:15 AM John Doe <john@example.com> wrote:\n"
            "> Can we meet tomorrow?\n"
            "> Let me know."
        )
    )
    result = _preprocessor().preprocess(email)
    assert result.body == "Thanks, sounds good."
    assert "wrote:" not in result.body
    assert "meet tomorrow" not in result.body


def test_original_message_banner_truncates_quoted_content() -> None:
    email = _email(
        body_text=(
            "See my reply below.\n\n"
            "-----Original Message-----\n"
            "From: someone@example.com\n"
            "Subject: Old thread"
        )
    )

    result = _preprocessor().preprocess(email)
    assert result.body == "See my reply below."
    assert "Original Message" not in result.body


def test_trailing_quote_block_is_stripped() -> None:
    email = _email(
        body_text="My actual reply.\n\n> Original question line one.\n> Original question line two."
    )
    result = _preprocessor().preprocess(email)
    assert result.body == "My actual reply."


def test_quote_marker_not_at_end_is_preserved() -> None:
    """A ">" appearing mid-message (not part of a trailing quote block)
    is not a reply artifact — must be left alone, per the "if uncertain,
    preserve the content" rule."""
    email = _email(body_text="Step 1: do this.\n> Step 2: then do that.\nStep 3: finish up.")
    result = _preprocessor().preprocess(email)
    assert "Step 2" in result.body
    assert "Step 3" in result.body


def test_email_without_reply_markers_is_unaffected() -> None:
    email = _email(body_text="Just a normal message with no reply history.")

    result = _preprocessor().preprocess(email)

    assert result.body == "Just a normal message with no reply history."


def test_standard_signature_delimiter_is_stripped() -> None:
    email = _email(body_text="See you at the meeting.\n\n--\nJane Doe\nCEO, Example Corp")
    result = _preprocessor().preprocess(email)
    assert result.body == "See you at the meeting."
    assert "CEO" not in result.body


def test_double_dash_within_a_sentence_is_not_treated_as_signature() -> None:
    """Only an exact "--" alone on its own line is the signature
    marker — "--" appearing as part of a real sentence must not
    trigger stripping."""
    email = _email(body_text="The result was -- surprisingly -- exactly what we expected.")

    result = _preprocessor().preprocess(email)

    assert "surprisingly" in result.body
    assert "exactly what we expected" in result.body


def test_email_without_signature_is_unaffected() -> None:
    email = _email(body_text="No signature block in this message at all.")

    result = _preprocessor().preprocess(email)

    assert result.body == "No signature block in this message at all."


def test_long_content_is_truncated() -> None:
    long_body = "A" * (AI_PREPROCESSING_MAX_BODY_CHARACTERS + 500)
    email = _email(body_text=long_body)

    result = _preprocessor().preprocess(email)

    assert result.truncated is True
    assert len(result.body) <= AI_PREPROCESSING_MAX_BODY_CHARACTERS
    assert result.body.endswith("...")


def test_content_within_limit_is_not_truncated() -> None:
    body = "A" * (AI_PREPROCESSING_MAX_BODY_CHARACTERS - 100)
    email = _email(body_text=body)

    result = _preprocessor().preprocess(email)

    assert result.truncated is False
    assert result.body == body


def test_content_exactly_at_limit_is_not_truncated() -> None:
    body = "A" * AI_PREPROCESSING_MAX_BODY_CHARACTERS
    email = _email(body_text=body)
    result = _preprocessor().preprocess(email)
    assert result.truncated is False
    assert result.body == body


def test_sender_is_preserved() -> None:
    email = _email(sender="specific-sender@example.com", body_text="Body.")
    result = _preprocessor().preprocess(email)
    assert result.sender == "specific-sender@example.com"


def test_subject_is_preserved() -> None:
    email = _email(subject="A Very Specific Subject", body_text="Body.")
    result = _preprocessor().preprocess(email)
    assert result.subject == "A Very Specific Subject"


def test_none_subject_is_preserved_as_none() -> None:
    email = _email(subject=None, body_text="Body.")
    result = _preprocessor().preprocess(email)
    assert result.subject is None


def test_recipients_are_preserved() -> None:
    email = _email(recipients=["a@example.com", "b@example.com"], body_text="Body.")
    result = _preprocessor().preprocess(email)
    assert result.recipients == ["a@example.com", "b@example.com"]


def test_empty_recipients_list_is_preserved() -> None:
    email = _email(recipients=[], body_text="Body.")
    result = _preprocessor().preprocess(email)
    assert result.recipients == []
