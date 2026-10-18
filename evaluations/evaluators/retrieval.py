"""Retrieval metrics over the raw Pinecone ranking (before context selection)."""

from __future__ import annotations


def recall_at_k(ranked_ids: list[str], groups: list[list[str]], k: int) -> float:
    """Fraction of evidence groups with at least one member in the top k."""
    if not groups:
        return 0.0
    top = set(ranked_ids[:k])
    return sum(1 for group in groups if top.intersection(group)) / len(groups)


def reciprocal_rank(ranked_ids: list[str], relevant: set[str]) -> float:
    for rank, chunk_id in enumerate(ranked_ids, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def context_recall(context_ids: list[str], groups: list[list[str]]) -> float:
    """Fraction of evidence groups that reached the generation context."""
    return recall_at_k(context_ids, groups, len(context_ids))
