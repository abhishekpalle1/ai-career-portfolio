"""Indirect prompt-injection screening for retrieved evidence."""

from __future__ import annotations

from app.guardrails.input_guard import contains_injection
from app.retrieval.vector_store import RetrievedChunk


def filter_unsafe_chunks(chunks: list[RetrievedChunk]) -> tuple[list[RetrievedChunk], int]:
    """Drop chunks carrying instructions aimed at the assistant. Returns (safe, dropped_count)."""
    safe = [chunk for chunk in chunks if not contains_injection(chunk.content)]
    return safe, len(chunks) - len(safe)
