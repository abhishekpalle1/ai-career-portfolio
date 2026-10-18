from __future__ import annotations

import re

from app.retrieval.vector_store import RetrievedChunk

# Same approximation as ingestion: words + punctuation.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def employer_of(chunk: RetrievedChunk) -> str | None:
    """Employer from a PROFESSIONAL heading path: `NAME > WORK EXPERIENCE > Employer, Role`."""
    parts = chunk.heading_path.split(" > ")
    if chunk.experience_type != "PROFESSIONAL" or len(parts) < 3:
        return None
    return parts[2].split(",")[0].strip() or None


def select_context(
    chunks: list[RetrievedChunk],
    *,
    final_chunks: int,
    min_score: float | None,
    max_context_tokens: int | None,
    diversify_employers: bool = False,
) -> list[RetrievedChunk]:
    """Score-ordered context; diversify_employers puts each employer's best chunk first."""
    ranked = sorted(chunks, key=lambda c: c.score, reverse=True)
    if diversify_employers:
        leaders: dict[str, RetrievedChunk] = {}
        for chunk in ranked:
            employer = employer_of(chunk)
            if employer is not None and (min_score is None or chunk.score >= min_score):
                leaders.setdefault(employer, chunk)
        first = {id(c) for c in leaders.values()}
        ranked = list(leaders.values()) + [c for c in ranked if id(c) not in first]
    selected: list[RetrievedChunk] = []
    seen: set[str] = set()
    used_tokens = 0
    for chunk in ranked:
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
    # Citation IDs follow context order, so keep the original ranking.
    return sorted(selected, key=lambda c: c.score, reverse=True)
