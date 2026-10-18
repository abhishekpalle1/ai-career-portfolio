"""PROFESSIONAL versus PORTFOLIO attribution checks."""

from __future__ import annotations

import re

from evaluations.corpus import CorpusChunk
from evaluations.evaluators.text import normalize, sentences


def _core_titles(titles: set[str]) -> set[str]:
    cores = set(titles)
    for title in titles:
        words = title.split()
        if len(words) >= 3:
            cores.add(" ".join(words[1:3]))
    return {normalize(t) for t in cores if len(t) >= 6}


def citation_attribution_checks(
    citations: list[tuple[str, str, str]], corpus: dict[str, CorpusChunk]
) -> tuple[int, int]:
    """citations: (chunk_id, section, experience_type). Returns (correct, total)."""
    correct = 0
    for chunk_id, section, experience_type in citations:
        truth = corpus.get(chunk_id)
        correct += bool(
            truth and truth.section == section and truth.experience_type == experience_type
        )
    return correct, len(citations)


def portfolio_misattributions(answer: str, titles: set[str], employers: set[str]) -> list[str]:
    """Sentences that place a portfolio project at an employer without calling it portfolio work."""
    cores = _core_titles(titles)
    employer_patterns = [
        re.compile(rf"\b{re.escape(normalize(e))}\b")
        for name in employers
        for e in {name, name.split()[0]}
        if len(e) >= 3 and (e == name or e.isupper())
    ]
    hits: list[str] = []
    for sentence in sentences(answer):
        folded = normalize(sentence)
        if (
            any(core in folded for core in cores)
            and any(p.search(folded) for p in employer_patterns)
            and "portfolio" not in folded
        ):
            hits.append(sentence[:160])
    return hits


def portfolio_labelled(answer: str) -> bool:
    return "portfolio" in normalize(answer)
