from datetime import UTC, datetime
from uuid import uuid4

from app.ai.context.draft_context import DraftContext, DraftContextBuilder
from app.ai.prompts.draft_prompt import build_draft_prompt
from app.ai.schemas.ai_understanding import (
    AIUnderstandingResult,
    EmailCategory,
    EmailIntent,
    EmailSentiment,
    EmailUrgency,
)
from app.ai.schemas.rag import EmailContextSection, RAGContext, RetrievedChunk
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
        subject="Flight Cancelled",
        snippet="snippet",
        body_text="Your flight has been cancelled. Please contact us immediately.",
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


def _understanding(**overrides) -> AIUnderstandingResult:
    defaults = dict(
        category=EmailCategory.TRAVEL,
        intent=EmailIntent.CANCELLATION,
        urgency=EmailUrgency.HIGH,
        sentiment=EmailSentiment.NEGATIVE,
        entities=[],
        summary="Flight booking was cancelled.",
        confidence=0.9,
    )
    defaults.update(overrides)
    return AIUnderstandingResult(**defaults)


def _retrieved_chunk(**overrides) -> RetrievedChunk:
    defaults = dict(
        email_id=uuid4(),
        thread_id=uuid4(),
        chunk_index=0,
        content="Relevant past content.",
        received_at=datetime.now(UTC),
        similarity=0.9,
    )
    defaults.update(overrides)
    return RetrievedChunk(**defaults)


def _rag_context_with_chunks(chunks: list[RetrievedChunk]) -> RAGContext:
    """Build a real RAGContext from a flat chunk list, grouped by
    email — mirrors what ContextBuilder (Task 6.7) actually produces,
    without importing that module (this test only needs a realistic
    RAGContext value, not the builder that makes one)."""
    sections: list[EmailContextSection] = []
    for chunk in chunks:
        sections.append(
            EmailContextSection(
                email_id=chunk.email_id,
                thread_id=chunk.thread_id,
                received_at=chunk.received_at,
                chunks=[chunk],
                text=chunk.content,
            )
        )
    return RAGContext(sections=sections, text="\n\n".join(s.text for s in sections))


def _builder() -> DraftContextBuilder:
    return DraftContextBuilder()


# ---------------------------------------------------------------------------
# 1. Full context
# ---------------------------------------------------------------------------


def test_full_context_preserves_all_three_inputs() -> None:
    email = _email()
    understanding = _understanding()
    retrieved_context = _rag_context_with_chunks([_retrieved_chunk(content="Past email content.")])

    context = _builder().build_context(
        email=email, understanding=understanding, retrieved_context=retrieved_context
    )

    assert context.email is email
    assert context.understanding is understanding
    assert context.retrieved_context is retrieved_context


def test_full_context_preserves_instructions_when_provided() -> None:
    context = _builder().build_context(
        email=_email(),
        understanding=_understanding(),
        instructions="Keep the reply under three sentences.",
    )

    assert context.instructions == "Keep the reply under three sentences."


# ---------------------------------------------------------------------------
# 2. Email + understanding without RAG
# ---------------------------------------------------------------------------


def test_context_without_retrieved_context_defaults_to_empty_rag_context() -> None:
    context = _builder().build_context(email=_email(), understanding=_understanding())

    assert isinstance(context.retrieved_context, RAGContext)
    assert context.retrieved_context.is_empty is True
    assert context.retrieved_context.sections == []
    assert context.retrieved_context.text == ""


# ---------------------------------------------------------------------------
# 3. Empty RAG context (explicitly passed, not omitted)
# ---------------------------------------------------------------------------


def test_explicitly_empty_rag_context_is_preserved_as_is() -> None:
    empty_context = RAGContext(sections=[], text="")

    context = _builder().build_context(
        email=_email(), understanding=_understanding(), retrieved_context=empty_context
    )

    assert context.retrieved_context is empty_context
    assert context.retrieved_context.is_empty is True


# ---------------------------------------------------------------------------
# 4. Optional AI fields
# ---------------------------------------------------------------------------


def test_understanding_with_no_entities_is_preserved() -> None:
    understanding = _understanding(entities=[])

    context = _builder().build_context(email=_email(), understanding=understanding)

    assert context.understanding.entities == []


def test_understanding_with_entities_is_preserved() -> None:
    understanding = _understanding(
        entities=[{"type": "organization", "value": "Delta Airlines"}]
    )

    context = _builder().build_context(email=_email(), understanding=understanding)

    assert len(context.understanding.entities) == 1
    assert context.understanding.entities[0].value == "Delta Airlines"


# ---------------------------------------------------------------------------
# 5. Multiple retrieved documents
# ---------------------------------------------------------------------------


def test_multiple_retrieved_chunks_are_all_preserved() -> None:
    chunks = [
        _retrieved_chunk(content="First relevant chunk.", similarity=0.95),
        _retrieved_chunk(content="Second relevant chunk.", similarity=0.88),
        _retrieved_chunk(content="Third relevant chunk.", similarity=0.81),
    ]
    retrieved_context = _rag_context_with_chunks(chunks)

    context = _builder().build_context(
        email=_email(), understanding=_understanding(), retrieved_context=retrieved_context
    )

    assert len(context.retrieved_context.sections) == 3
    assert "First relevant chunk." in context.retrieved_context.text
    assert "Second relevant chunk." in context.retrieved_context.text
    assert "Third relevant chunk." in context.retrieved_context.text


# ---------------------------------------------------------------------------
# 6. Retrieved ordering is preserved
# ---------------------------------------------------------------------------


def test_retrieved_context_ordering_is_not_altered() -> None:
    """DraftContextBuilder must not re-rank or reorder — whatever
    order RAGContext.sections arrived in is the order it leaves in."""
    chunks = [
        _retrieved_chunk(content="most relevant", similarity=0.99),
        _retrieved_chunk(content="second most relevant", similarity=0.5),
        _retrieved_chunk(content="least relevant", similarity=0.1),
    ]
    retrieved_context = _rag_context_with_chunks(chunks)
    original_order = [s.email_id for s in retrieved_context.sections]

    context = _builder().build_context(
        email=_email(), understanding=_understanding(), retrieved_context=retrieved_context
    )

    assert [s.email_id for s in context.retrieved_context.sections] == original_order


# ---------------------------------------------------------------------------
# 7. Special characters / Unicode
# ---------------------------------------------------------------------------


def test_unicode_and_special_characters_are_preserved() -> None:
    email = _email(
        sender="José García <jose@example.com>",
        subject="日本語のテスト — résumé",
        body_text="Café résumé — 50% off! \"quoted\" & 'apostrophe'.",
    )

    context = _builder().build_context(email=email, understanding=_understanding())

    assert context.email.sender == "José García <jose@example.com>"
    assert context.email.subject == "日本語のテスト — résumé"
    assert context.email.body_text == "Café résumé — 50% off! \"quoted\" & 'apostrophe'."


# ---------------------------------------------------------------------------
# 8. Required input validation
# ---------------------------------------------------------------------------


def test_missing_email_raises_type_error() -> None:
    """DraftContext follows the same convention every other plain-
    dataclass pipeline type in this project uses (ParsedEmail,
    EmailChunk): required fields have no default, so Python's own
    dataclass machinery raises TypeError on a missing argument — no
    custom validation layer is added on top of that."""
    import pytest

    with pytest.raises(TypeError):
        DraftContext(understanding=_understanding(), retrieved_context=RAGContext())  # type: ignore[call-arg]


def test_missing_understanding_raises_type_error() -> None:
    import pytest

    with pytest.raises(TypeError):
        DraftContext(email=_email(), retrieved_context=RAGContext())  # type: ignore[call-arg]


def test_builder_requires_email_and_understanding_as_keyword_args() -> None:
    import pytest

    with pytest.raises(TypeError):
        _builder().build_context()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 9. Compatibility with the Phase 7.3 prompt builder
# ---------------------------------------------------------------------------


def test_draft_context_fields_are_directly_consumable_by_build_draft_prompt() -> None:
    """Proves structural compatibility without introducing a coupling
    method in production code: DraftContext's fields map directly
    onto build_draft_prompt's keyword parameters."""
    email = _email(body_text="Distinctive body for compatibility check.")
    understanding = _understanding(summary="Distinctive summary for compatibility check.")
    retrieved_context = _rag_context_with_chunks([_retrieved_chunk(content="Distinctive retrieved text.")])

    context = _builder().build_context(
        email=email, understanding=understanding, retrieved_context=retrieved_context
    )

    prompt = build_draft_prompt(
        email=context.email, understanding=context.understanding, context=context.retrieved_context
    )

    assert "Distinctive body for compatibility check." in prompt
    assert "Distinctive summary for compatibility check." in prompt
    assert "Distinctive retrieved text." in prompt


def test_compatibility_holds_with_default_empty_retrieved_context() -> None:
    context = _builder().build_context(email=_email(), understanding=_understanding())

    prompt = build_draft_prompt(
        email=context.email, understanding=context.understanding, context=context.retrieved_context
    )

    assert "No relevant historical context was found." in prompt


# ---------------------------------------------------------------------------
# 10. Input objects are not mutated
# ---------------------------------------------------------------------------


def test_email_input_is_not_mutated() -> None:
    email = _email(recipients=["a@example.com", "b@example.com"], subject="Original Subject")
    original_recipients = list(email.recipients)
    original_subject = email.subject

    _builder().build_context(email=email, understanding=_understanding())

    assert email.recipients == original_recipients
    assert email.subject == original_subject


def test_understanding_input_is_not_mutated() -> None:
    understanding = _understanding(
        entities=[{"type": "organization", "value": "Delta Airlines"}], confidence=0.77
    )
    original_entities_count = len(understanding.entities)
    original_confidence = understanding.confidence

    _builder().build_context(email=_email(), understanding=understanding)

    assert len(understanding.entities) == original_entities_count
    assert understanding.confidence == original_confidence


def test_retrieved_context_input_is_not_mutated() -> None:
    retrieved_context = _rag_context_with_chunks(
        [_retrieved_chunk(content="A"), _retrieved_chunk(content="B")]
    )
    original_section_count = len(retrieved_context.sections)
    original_text = retrieved_context.text

    _builder().build_context(
        email=_email(), understanding=_understanding(), retrieved_context=retrieved_context
    )

    assert len(retrieved_context.sections) == original_section_count
    assert retrieved_context.text == original_text