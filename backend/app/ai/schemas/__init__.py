"""Typed schemas for AI-produced data.

Distinct from app/presentation/api/v1/schemas/ (API request/response
contracts) and app/application/dto/ (plain dataclasses for
inter-layer handoffs like ParsedEmail) — schemas in this package are
Pydantic models specifically because they are the validation target
for structured LLM output (Task 5.4 parses a model's JSON response
directly into these types), where Pydantic's own parsing/validation is
the whole point, not just a nice-to-have.
"""
