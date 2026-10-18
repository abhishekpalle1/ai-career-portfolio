"""Citation precision/recall/validity, material-claim coverage, and unsupported-claim detection."""

from __future__ import annotations

import re

from evaluations.corpus import CorpusChunk
from evaluations.evaluators.text import (
    MARKER_RE,
    affirmative_matches,
    inline_citation_ids,
    normalize,
    normalized_numbers_in,
    number_key,
    number_keys,
    numeric_tokens,
    sentences,
)


def citation_precision(cited_chunk_ids: list[str], allowed: set[str]) -> tuple[int, int]:
    """(relevant citations, total citations)."""
    return sum(1 for cid in cited_chunk_ids if cid in allowed), len(cited_chunk_ids)


def citation_recall(cited_chunk_ids: list[str], groups: list[list[str]]) -> float:
    if not groups:
        return 0.0
    cited = set(cited_chunk_ids)
    return sum(1 for group in groups if cited.intersection(group)) / len(groups)


def citation_validity_issues(
    answer: str, citation_ids: list[str], cited_chunk_ids: list[str], context_ids: list[str]
) -> list[str]:
    issues: list[str] = []
    if not inline_citation_ids(answer) <= set(citation_ids):
        issues.append("inline_marker_without_returned_citation")
    if not set(cited_chunk_ids) <= set(context_ids):
        issues.append("citation_not_in_request_context")
    if len(set(citation_ids)) != len(citation_ids):
        issues.append("duplicate_citation_ids")
    return issues


def material_claim_coverage(answer: str, entities: set[str]) -> tuple[int, int]:
    """(cited material sentences, material sentences). Material = has a number or named entity."""
    folded = {normalize(e) for e in entities}
    material = covered = 0
    for sentence in sentences(answer):
        body = normalize(MARKER_RE.sub(" ", sentence))
        if re.search(r"\d", body) or any(e in body for e in folded):
            material += 1
            covered += bool(MARKER_RE.search(sentence))
    return covered, material


def unsupported_claims(
    answer: str,
    cited: list[CorpusChunk],
    employers: set[str],
    forbidden_patterns: list[str],
) -> list[str]:
    """Deterministic proxy: numbers and employers in the answer must appear in cited evidence."""
    evidence = " ".join(chunk.content for chunk in cited)
    evidence_numbers = normalized_numbers_in(evidence)
    evidence_keys = number_keys(evidence)
    issues = [
        f"number_not_in_cited_evidence:{token}"
        for token in sorted(numeric_tokens(answer))
        if token.rstrip("+%KM")
        and token not in evidence_numbers
        and number_key(token) not in evidence_keys
    ]
    answer_folded, evidence_folded = normalize(answer), normalize(evidence)
    issues += [
        f"employer_not_in_cited_evidence:{name}"
        for name in sorted(employers)
        if normalize(name) in answer_folded and normalize(name) not in evidence_folded
    ]
    issues += [f"forbidden_claim:{p}" for p in affirmative_matches(answer, forbidden_patterns)]
    return issues
