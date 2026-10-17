from __future__ import annotations

import re

from app.retrieval.vector_store import RetrievedChunk

# Same approximation as ingestion: words + punctuation.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def select_context(
    chunks: list[RetrievedChunk],
    *,
    final_chunks: int,
    min_score: float | None,
    max_context_tokens: int | None,
) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    seen: set[str] = set()
    used_tokens = 0
    for chunk in sorted(chunks, key=lambda c: c.score, reverse=True):
        if min_score is not None and chunk.score < min_score:
            continue
        dedupe_key = chunk.content_hash or chunk.content
        if chunk.chunk_id in seen or dedupe_key in seen:
            continue
        tokens = count_tokens(chunk.content)
        if max_context_tokens is not None and used_tokens + tokens > max_context_tokens:
            continue
        seen.update({chunk.chunk_id, dedupe_key})
        used_tokens += tokens
        selected.append(chunk)
        if len(selected) >= final_chunks:
            break
    return selected
