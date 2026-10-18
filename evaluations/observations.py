"""Raw per-case observations. Scoring is a pure function of observations, so it runs offline."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class CitationObservation(BaseModel):
    citation_id: str
    chunk_id: str
    section: str
    experience_type: str
    source_url: str


class ResponseObservation(BaseModel):
    answer: str
    intent: str
    grounded: bool
    abstained: bool
    citations: list[CitationObservation]
    suggested_questions: list[str]


class Observation(BaseModel):
    case_id: str
    mode: Literal["offline", "live"]
    blocked: bool
    guard_category: str | None = None
    redirected: bool = False
    intent: str | None = None
    outcome: str | None = None
    retrieved: list[tuple[str, float]] = []
    context_ids: list[str] = []
    response: ResponseObservation | None = None
    # Generated answer with [Cn] markers, before the backend strips them for display.
    internal_answer: str | None = None
    claims: int = 0
    error: str | None = None
    embed_requests: int = 0
    pinecone_queries: int = 0
    generations: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    latency_ms: int = 0


def save_observations(path: Path, observations: list[Observation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(o.model_dump_json() + "\n" for o in observations), encoding="utf-8")


def load_observations(path: Path) -> list[Observation]:
    return [
        Observation.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
