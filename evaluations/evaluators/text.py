"""Text helpers owned by the evaluator. Deliberately independent of app.guardrails."""

from __future__ import annotations

import re
import unicodedata

_SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+(?=[A-Z\"'(\-])|\n+")
_NEGATION_RE = re.compile(
    r"\b(?:not|never|no|none|neither|nor|without|lacks?|absent|rather than|instead of)\b"
    r"|n['\u2019]t\b",
    re.IGNORECASE,
)
MARKER_RE = re.compile(r"\[\s*C\d+(?:\s*,\s*C\d+)*\s*\]")
MARKER_ID_RE = re.compile(r"C\d+")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*(?:\s?%|[KkMm]\b|\+)?")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\u2019", "'").replace("\u2013", "-")
    text = text.replace("&", " and ")
    return re.sub(r"\s+", " ", text).strip().casefold()


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]


def is_negated(sentence: str) -> bool:
    return bool(_NEGATION_RE.search(sentence))


def affirmative_matches(text: str, patterns: list[str]) -> list[str]:
    """Forbidden patterns matched in sentences that are not negated."""
    hits: list[str] = []
    for sentence in sentences(text):
        if is_negated(sentence):
            continue
        hits.extend(p for p in patterns if re.search(p, sentence, re.IGNORECASE))
    return sorted(set(hits))


def contains_fact(text: str, fact: str) -> bool:
    """`|` separates acceptable alternatives; numeric facts match by value (3K == 3,000)."""
    for option in fact.split("|"):
        key = number_key(option.strip())
        if key is not None and _NUMBER_RE.fullmatch(option.strip()):
            if key in number_keys(text):
                return True
        elif normalize(option) in normalize(text):
            return True
    return False


def inline_citation_ids(text: str) -> set[str]:
    return {cid for marker in MARKER_RE.findall(text) for cid in MARKER_ID_RE.findall(marker)}


def numeric_tokens(text: str) -> set[str]:
    stripped = MARKER_RE.sub(" ", text)
    return {re.sub(r"\s+", "", token).upper() for token in _NUMBER_RE.findall(stripped)}


def normalized_numbers_in(text: str) -> str:
    return re.sub(r"\s+", "", MARKER_RE.sub(" ", text)).upper()


_MULTIPLIERS = {"K": 1_000, "M": 1_000_000}


def number_key(token: str) -> tuple[float, bool] | None:
    """(value, is_percent) so equivalent spellings compare equal: 3K, 3,000, 400+ -> 400."""
    match = re.fullmatch(r"([\d.,]+)\s?(%|[KkMm])?\+?", token.strip())
    if match is None:
        return None
    digits, suffix = match.group(1).replace(",", ""), (match.group(2) or "").upper()
    try:
        value = float(digits)
    except ValueError:
        return None
    return round(value * _MULTIPLIERS.get(suffix, 1), 6), suffix == "%"


def number_keys(text: str) -> set[tuple[float, bool]]:
    return {key for token in numeric_tokens(text) if (key := number_key(token)) is not None}
