"""Draft-context composition (Phase 7, Task 7.4).

Combines already-available data (the original Email, its Phase 5
AIUnderstandingResult, and Phase 6 RAGContext) into a single
DraftContext for the Phase 7.3 prompt builder to consume. Performs no
LLM call, no retrieval, and no database/Gmail/ChromaDB access — purely
data composition.
"""