from datetime import datetime
from uuid import UUID

from app.ai.schemas.rag import EmailContextSection, RAGContext, RetrievedChunk


def _format_section(
    email_id: UUID, thread_id: UUID, received_at: datetime, ordered_chunks: list[RetrievedChunk]
) -> str:
    header = f"Email {email_id} (received {received_at.date().isoformat()}):"
    body = "\n".join(chunk.content for chunk in ordered_chunks)
    return f"{header}\n{body}"


class ContextBuilder:
    def build_context(self, retrieved_chunks: list[RetrievedChunk]) -> RAGContext:
        if not retrieved_chunks:
            return RAGContext(sections=[], text="")

        chunks_by_email: dict[UUID, list[RetrievedChunk]] = {}
        email_order: list[UUID] = []

        for chunk in retrieved_chunks:
            if chunk.email_id not in chunks_by_email:
                chunks_by_email[chunk.email_id] = []
                email_order.append(chunk.email_id)
            chunks_by_email[chunk.email_id].append(chunk)

        sections: list[EmailContextSection] = []
        for email_id in email_order:
            group = chunks_by_email[email_id]
            ordered_chunks = sorted(group, key=lambda c: c.chunk_index)

            thread_id = ordered_chunks[0].thread_id
            received_at = ordered_chunks[0].received_at
            section_text = _format_section(email_id, thread_id, received_at, ordered_chunks)

            sections.append(
                EmailContextSection(
                    email_id=email_id,
                    thread_id=thread_id,
                    received_at=received_at,
                    chunks=ordered_chunks,
                    text=section_text,
                )
            )

        full_text = "\n\n".join(section.text for section in sections)
        return RAGContext(sections=sections, text=full_text)
