from datetime import UTC, datetime
from uuid import uuid4

from app.ai.rag.context_builder import ContextBuilder
from app.ai.schemas.rag import RetrievedChunk


def _chunk(
    *,
    email_id=None,
    thread_id=None,
    chunk_index=0,
    content="content",
    received_at=None,
    similarity=0.9,
):
    return RetrievedChunk(
        email_id=email_id or uuid4(),
        thread_id=thread_id or uuid4(),
        chunk_index=chunk_index,
        content=content,
        received_at=received_at or datetime(2026, 1, 1, tzinfo=UTC),
        similarity=similarity,
    )


def _builder() -> ContextBuilder:
    return ContextBuilder()


def test_empty_input_produces_empty_context() -> None:
    result = _builder().build_context([])

    assert result.sections == []
    assert result.text == ""
    assert result.is_empty is True


def test_single_chunk_produces_one_section() -> None:
    email_id = uuid4()
    thread_id = uuid4()
    chunk = _chunk(email_id=email_id, thread_id=thread_id, content="Hello there.")

    result = _builder().build_context([chunk])

    assert len(result.sections) == 1
    assert result.sections[0].email_id == email_id
    assert result.sections[0].thread_id == thread_id
    assert result.is_empty is False
    assert "Hello there." in result.text


def test_single_chunk_text_includes_email_id_for_traceability() -> None:
    email_id = uuid4()
    chunk = _chunk(email_id=email_id, content="Some content.")

    result = _builder().build_context([chunk])

    assert str(email_id) in result.sections[0].text
    assert str(email_id) in result.text


def test_chunks_from_the_same_email_are_grouped_into_one_section() -> None:
    email_id = uuid4()
    chunks = [
        _chunk(email_id=email_id, chunk_index=0, content="First part."),
        _chunk(email_id=email_id, chunk_index=1, content="Second part."),
        _chunk(email_id=email_id, chunk_index=2, content="Third part."),
    ]

    result = _builder().build_context(chunks)

    assert len(result.sections) == 1
    assert len(result.sections[0].chunks) == 3


def test_chunks_from_different_emails_produce_separate_sections() -> None:
    chunks = [_chunk(email_id=uuid4()), _chunk(email_id=uuid4()), _chunk(email_id=uuid4())]

    result = _builder().build_context(chunks)

    assert len(result.sections) == 3
    assert len({s.email_id for s in result.sections}) == 3


def test_chunks_within_a_section_are_ordered_by_chunk_index() -> None:
    email_id = uuid4()
    chunks = [
        _chunk(email_id=email_id, chunk_index=2, content="third", similarity=0.95),
        _chunk(email_id=email_id, chunk_index=0, content="first", similarity=0.80),
        _chunk(email_id=email_id, chunk_index=1, content="second", similarity=0.90),
    ]

    result = _builder().build_context(chunks)

    ordered_indexes = [c.chunk_index for c in result.sections[0].chunks]
    assert ordered_indexes == [0, 1, 2]

    text = result.sections[0].text
    assert text.index("first") < text.index("second") < text.index("third")


def test_section_order_follows_first_appearance_in_retrieval_order() -> None:
    """No re-ranking happens here — the order sections appear in the
    output must match the order their first (most relevant) chunk was
    encountered while scanning retrieval's already-ordered input."""
    email_a = uuid4()
    email_b = uuid4()
    chunks = [
        _chunk(email_id=email_b, chunk_index=0, similarity=0.95),  # most relevant chunk overall
        _chunk(email_id=email_a, chunk_index=0, similarity=0.90),
        _chunk(email_id=email_b, chunk_index=1, similarity=0.85),
    ]

    result = _builder().build_context(chunks)

    assert [s.email_id for s in result.sections] == [email_b, email_a]


def test_section_retains_thread_id_and_received_at() -> None:
    thread_id = uuid4()
    received_at = datetime(2026, 3, 15, tzinfo=UTC)
    chunk = _chunk(thread_id=thread_id, received_at=received_at)

    result = _builder().build_context([chunk])

    assert result.sections[0].thread_id == thread_id
    assert result.sections[0].received_at == received_at


def test_section_chunks_retain_original_retrieved_chunk_objects() -> None:
    email_id = uuid4()
    original_chunk = _chunk(email_id=email_id, content="Traceable content.")

    result = _builder().build_context([original_chunk])

    assert result.sections[0].chunks[0] is original_chunk


def test_build_context_is_deterministic_across_repeated_calls() -> None:
    email_a = uuid4()
    email_b = uuid4()
    chunks = [
        _chunk(email_id=email_a, chunk_index=1, content="a1"),
        _chunk(email_id=email_b, chunk_index=0, content="b0"),
        _chunk(email_id=email_a, chunk_index=0, content="a0"),
    ]
    builder = _builder()

    first_result = builder.build_context(chunks)
    second_result = builder.build_context(chunks)

    assert first_result.text == second_result.text
    assert [s.email_id for s in first_result.sections] == [
        s.email_id for s in second_result.sections
    ]


def test_full_text_joins_all_sections() -> None:
    chunks = [
        _chunk(email_id=uuid4(), content="First email content."),
        _chunk(email_id=uuid4(), content="Second email content."),
    ]

    result = _builder().build_context(chunks)

    assert "First email content." in result.text
    assert "Second email content." in result.text
    assert result.text.count("\n\n") >= 1  # sections are separated, not concatenated raw
