from app.ai.preprocessing import PreprocessedEmail
from app.ai.rag.chunker import EmailChunker
from app.core.constants import CHUNK_SIZE


def _make_email(body: str) -> PreprocessedEmail:
    return PreprocessedEmail(
        sender="alice@example.com",
        recipients=["bob@example.com"],
        subject="Test Subject",
        body=body,
        truncated=False,
    )


def test_chunker_empty_body() -> None:
    chunker = EmailChunker()
    chunks = chunker.chunk(_make_email(""))
    assert len(chunks) == 0


def test_chunker_whitespace_body() -> None:
    chunker = EmailChunker()
    chunks = chunker.chunk(_make_email("   \n\t  "))
    assert len(chunks) == 0


def test_chunker_short_body() -> None:
    chunker = EmailChunker()
    text = "Hello, this is a short email body."
    chunks = chunker.chunk(_make_email(text))
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == text


def test_chunker_exactly_target_size() -> None:
    chunker = EmailChunker()
    text = "a" * CHUNK_SIZE
    chunks = chunker.chunk(_make_email(text))
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert len(chunks[0].content) == CHUNK_SIZE


def test_chunker_over_target_size_with_word_boundary() -> None:
    chunker = EmailChunker()
    word = "word "
    repeats = (CHUNK_SIZE * 2) // len(word)
    text = word * repeats

    chunks = chunker.chunk(_make_email(text))
    assert len(chunks) > 1

    # Verify chunk indexing sequence
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert len(c.content) <= CHUNK_SIZE

    # Verify overlap between consecutive chunks
    c0 = chunks[0].content
    c1 = chunks[1].content
    assert c0[-20:] in c1[:100]


def test_chunker_hard_split_fallback() -> None:
    chunker = EmailChunker()
    # A single continuous string without spaces
    text = "x" * (CHUNK_SIZE + 200)

    chunks = chunker.chunk(_make_email(text))
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert len(chunks[0].content) == CHUNK_SIZE


def test_chunker_determinism() -> None:
    chunker = EmailChunker()
    text = "Quick brown fox jumps over the lazy dog. " * 30

    email = _make_email(text)
    run1 = chunker.chunk(email)
    run2 = chunker.chunk(email)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2, strict=True):
        assert c1.chunk_index == c2.chunk_index
        assert c1.content == c2.content
