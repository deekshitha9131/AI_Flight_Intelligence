from app.ai.schemas.preprocessing import PreprocessedEmail
from app.ai.schemas.rag import EmailChunk
from app.core.constants import CHUNK_OVERLAP, CHUNK_SIZE


class EmailChunker:
    """Chunks preprocessed email body into overlapping text spans for
    vector indexing."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(self, email: PreprocessedEmail) -> list[EmailChunk]:
        text = email.body.strip() if email.body else ""
        if not text:
            return []

        if len(text) <= self._chunk_size:
            return [EmailChunk(chunk_index=0, content=text)]

        chunks: list[EmailChunk] = []
        start = 0
        text_len = len(text)
        chunk_index = 0

        while start < text_len:
            end_candidate = min(start + self._chunk_size, text_len)

            if end_candidate == text_len:
                chunk_str = text[start:end_candidate]
                chunks.append(EmailChunk(chunk_index=chunk_index, content=chunk_str))
                break

            # Try to break at a word boundary (space or newline)
            break_pos = -1
            min_boundary_start = start + self._chunk_overlap + 1
            for pos in range(end_candidate, min_boundary_start - 1, -1):
                if text[pos - 1] in (" ", "\n", "\t", "\r"):
                    break_pos = pos
                    break

            end = break_pos if break_pos != -1 else end_candidate

            chunk_str = text[start:end]
            chunks.append(EmailChunk(chunk_index=chunk_index, content=chunk_str))
            chunk_index += 1

            next_start = end - self._chunk_overlap
            if next_start <= start:
                next_start = end
            start = next_start

        return chunks
