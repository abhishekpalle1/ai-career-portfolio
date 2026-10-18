"""Deterministic output guardrails applied after citation validation.

Verdicts: PASS returns the answer; REPAIRABLE may be regenerated (MAX_GENERATION_RETRIES, default
0); FAIL always becomes a safe abstention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.retrieval.vector_store import RetrievedChunk

Verdict = Literal["PASS", "REPAIRABLE", "FAIL"]

REDACTION = "[redacted]"

_SECRET_RE = re.compile(
    r"AIza[0-9A-Za-z_-]{20,}|\bsk-[A-Za-z0-9_-]{20,}|\bpcsk_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}"
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<![\w.])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\w|\.\d)")
_PROMPT_LEAK_RE = re.compile(
    r"retrieved_evidence|\[CHUNK C\d+\]|untrusted (reference )?evidence"
    r"|Recruiter question \(untrusted\)"
    r"|AI Career Portfolio Assistant\.\s*Answer only|\bcontent_hash\b|\bingestion_status\b"
    r"|\bchunk_id\b|\bsource_id\b|\bheading_path\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"\b(?:https?|javascript|vbscript|data|file|ftp)\s*:", re.IGNORECASE)
_HTML_RE = re.compile(r"<\s*/?\s*[a-z][^>]*>", re.IGNORECASE)
_MARKER_RE = re.compile(r"\[\s*C\d+(?:\s*,\s*C\d+)*\s*\]")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\-])|\n+")
# Negative assertions about Abhishek. Statements about the documents are allowed (see _DOCUMENT_RE).
_NEGATION_RE = re.compile(
    r"\b(?:not|never|no|none|neither|nor|without)\b|n['\u2019]t\b", re.IGNORECASE
)
_ALLOWED_NEGATION_RE = re.compile(r"\bnot only\b|\bno\.\s*\d", re.IGNORECASE)
_DOCUMENT_RE = re.compile(
    r"\b(r[eé]sum[eé]|approved (?:materials?|evidence|sources?)|materials?|evidence|sources?|"
    r"document(?:s|ed|ation)?|listed|lists?|mentions?|mentioned|records?|portfolio project)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OutputVerdict:
    verdict: Verdict
    reason: str | None
    answer: str


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _employers(context: list[RetrievedChunk]) -> set[str]:
    employers: set[str] = set()
    for chunk in context:
        parts = chunk.heading_path.split(" > ")
        if chunk.experience_type == "PROFESSIONAL" and len(parts) >= 3:
            name = parts[2].split(",")[0].strip()
            if name:
                employers.add(name)
                first = name.split()[0]
                if first.isupper():
                    employers.add(first)
    return {e for e in employers if len(e) >= 3}


def _portfolio_titles(context: list[RetrievedChunk]) -> set[str]:
    titles: set[str] = set()
    for chunk in context:
        parts = chunk.heading_path.split(" > ")
        if chunk.experience_type == "PORTFOLIO" and len(parts) >= 3:
            title = parts[-1].strip()
            titles.add(title)
            # Distinctive core, e.g. "Commercial Auto" from "Agentic Commercial Auto Underwriting".
            words = title.split()
            if len(words) >= 3:
                titles.add(" ".join(words[1:3]))
    return {t for t in titles if len(t) >= 6}


def check_output(
    answer: str, context: list[RetrievedChunk], *, max_characters: int
) -> OutputVerdict:
    if _SECRET_RE.search(answer):
        return OutputVerdict("FAIL", "secret_in_output", answer)
    if _PROMPT_LEAK_RE.search(answer):
        return OutputVerdict("FAIL", "prompt_or_metadata_leak", answer)
    if _URL_RE.search(answer) or _HTML_RE.search(answer):
        return OutputVerdict("FAIL", "url_or_html_in_output", answer)

    redacted = _PHONE_RE.sub(REDACTION, _EMAIL_RE.sub(REDACTION, answer))

    if len(redacted) > max_characters:
        return OutputVerdict("REPAIRABLE", "answer_too_long", redacted)

    employers = _employers(context)
    titles = _portfolio_titles(context)
    for sentence in _sentences(redacted):
        without_markers = _MARKER_RE.sub("", sentence)
        if re.search(r"\d", without_markers) and not _MARKER_RE.search(sentence):
            return OutputVerdict("REPAIRABLE", "uncited_fact", redacted)
        if sentence.lstrip().startswith("- ") and not _MARKER_RE.search(sentence):
            return OutputVerdict("REPAIRABLE", "uncited_bullet", redacted)
        if _NEGATION_RE.search(
            _ALLOWED_NEGATION_RE.sub("", without_markers)
        ) and not _DOCUMENT_RE.search(without_markers):
            return OutputVerdict("FAIL", "unsupported_negative_assertion", redacted)
        lowered = without_markers.casefold()
        if (
            any(t.casefold() in lowered for t in titles)
            and any(re.search(rf"\b{re.escape(e.casefold())}\b", lowered) for e in employers)
            and "portfolio" not in lowered
        ):
            return OutputVerdict("FAIL", "portfolio_attributed_to_employer", redacted)

    return OutputVerdict("PASS", None, redacted)
