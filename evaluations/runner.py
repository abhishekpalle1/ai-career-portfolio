"""Collect observations. Offline: deterministic guards only. Live: the real guarded RAG pipeline."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Sequence
from typing import Any

from app.core.config import Settings
from app.guardrails.cost_controls import AnswerCache
from app.guardrails.input_guard import check_input
from app.models.chat import ChatResponse
from app.retrieval.vector_store import RetrievedChunk
from app.services.generation import GeneratedAnswer
from app.services.intent import classify_intent
from app.services.rag_assistant import (
    AssistantUnavailableError,
    RagAssistant,
    build_live_components,
)
from evaluations.dataset import EvalCase
from evaluations.observations import CitationObservation, Observation, ResponseObservation

REDIRECT_INTENTS = frozenset({"CONTACT_INFORMATION", "RESUME_REQUEST"})


def observe_offline(cases: Sequence[EvalCase]) -> list[Observation]:
    observations: list[Observation] = []
    for case in cases:
        verdict = check_input(case.question)
        intent = classify_intent(case.question) if verdict.allowed else None
        observations.append(
            Observation(
                case_id=case.case_id,
                mode="offline",
                blocked=not verdict.allowed,
                guard_category=verdict.category,
                intent=intent,
                redirected=intent in REDIRECT_INTENTS,
            )
        )
    return observations


class _Recorder:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.embed_requests = self.pinecone_queries = self.generations = 0
        self.retrieved: list[tuple[str, float]] = []
        self.context_ids: list[str] = []
        self.usage = {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}
        self.outcome: str | None = None
        self.generated: GeneratedAnswer | None = None


class _RecordingEmbedder:
    def __init__(self, inner: Any, recorder: _Recorder) -> None:
        self._inner, self._rec = inner, recorder

    def embed_query(self, text: str) -> list[float]:
        self._rec.embed_requests += 1
        return list(self._inner.embed_query(text))


class _RecordingRetriever:
    def __init__(self, inner: Any, recorder: _Recorder) -> None:
        self._inner, self._rec = inner, recorder

    def retrieve(self, vector: list[float], top_k: int) -> list[RetrievedChunk]:
        self._rec.pinecone_queries += 1
        chunks: list[RetrievedChunk] = self._inner.retrieve(vector, top_k)
        self._rec.retrieved = [(c.chunk_id, round(c.score, 6)) for c in chunks]
        return chunks


class _RecordingGenerator:
    def __init__(self, inner: Any, recorder: _Recorder) -> None:
        self._inner, self._rec = inner, recorder

    def generate(self, question: str, context: list[RetrievedChunk]) -> GeneratedAnswer | None:
        self._rec.generations += 1
        self._rec.context_ids = [c.chunk_id for c in context]
        result: GeneratedAnswer | None = self._inner.generate(question, context)
        self._rec.generated = result
        for key, value in getattr(self._inner, "last_usage", {}).items():
            self._rec.usage[key] = self._rec.usage.get(key, 0) + int(value)
        return result


class _OutcomeHandler(logging.Handler):
    def __init__(self, recorder: _Recorder) -> None:
        super().__init__(level=logging.INFO)
        self._rec = recorder

    def emit(self, record: logging.LogRecord) -> None:
        match = re.search(r"\boutcome=(\S+)", record.getMessage())
        if match:
            self._rec.outcome = match.group(1)


def _response_observation(response: ChatResponse) -> ResponseObservation:
    return ResponseObservation(
        answer=response.answer,
        intent=response.intent,
        grounded=response.grounded,
        abstained=response.abstained,
        citations=[
            CitationObservation(
                citation_id=c.citation_id,
                chunk_id=c.chunk_id,
                section=c.section,
                experience_type=c.experience_type,
                source_url=c.source_url,
            )
            for c in response.citations
        ],
        suggested_questions=response.suggested_questions,
    )


def observe_live(
    cases: Sequence[EvalCase],
    settings: Settings,
    *,
    min_interval_seconds: float,
    skip_generation: bool = False,
    progress: Callable[[str], None] = print,
) -> tuple[list[Observation], str | None]:
    """Returns (observations, stop_reason). Stops on the first provider failure; never retries."""
    recorder = _Recorder()
    embedder, retriever, generator = build_live_components(settings)
    rec_embedder = _RecordingEmbedder(embedder, recorder)
    rec_retriever = _RecordingRetriever(retriever, recorder)
    # Cache disabled so every case measures a fresh pipeline run.
    assistant = RagAssistant(
        settings,
        rec_embedder,
        rec_retriever,
        _RecordingGenerator(generator, recorder),
        cache=AnswerCache(ttl_seconds=0, max_entries=0),
    )
    rag_logger = logging.getLogger("career-portfolio.rag")
    handler = _OutcomeHandler(recorder)
    previous_level = rag_logger.level
    rag_logger.addHandler(handler)
    rag_logger.setLevel(logging.INFO)

    observations: list[Observation] = []
    stop_reason: str | None = None
    last_call = 0.0
    try:
        for index, case in enumerate(cases, start=1):
            recorder.reset()
            verdict = check_input(case.question)
            needs_calls = verdict.allowed and classify_intent(case.question) not in (
                REDIRECT_INTENTS | {"OUT_OF_SCOPE"}
            )
            if needs_calls:
                wait = min_interval_seconds - (time.monotonic() - last_call)
                if wait > 0:
                    time.sleep(wait)
                last_call = time.monotonic()
            started = time.perf_counter()
            obs = Observation(
                case_id=case.case_id,
                mode="live",
                blocked=not verdict.allowed,
                guard_category=verdict.category,
            )
            try:
                if skip_generation:
                    if needs_calls:
                        rec_retriever.retrieve(
                            rec_embedder.embed_query(case.question), settings.retrieval_top_k
                        )
                else:
                    response = assistant.answer(case.question)
                    obs.response = _response_observation(response)
                    obs.intent = response.intent
                    obs.redirected = response.intent in REDIRECT_INTENTS and not response.citations
            except AssistantUnavailableError:
                obs.error = "dependency_failure"
                stop_reason = f"provider failure on {case.case_id}; run stopped without retry"
            obs.outcome = recorder.outcome
            if recorder.generated is not None:
                obs.internal_answer = recorder.generated.answer
                obs.claims = len(recorder.generated.claims)
            obs.retrieved = list(recorder.retrieved)
            obs.context_ids = list(recorder.context_ids)
            obs.embed_requests = recorder.embed_requests
            obs.pinecone_queries = recorder.pinecone_queries
            obs.generations = recorder.generations
            obs.input_tokens = recorder.usage["input_tokens"]
            obs.output_tokens = recorder.usage["output_tokens"]
            obs.thinking_tokens = recorder.usage["thinking_tokens"]
            obs.latency_ms = int((time.perf_counter() - started) * 1000)
            observations.append(obs)
            progress(
                f"[{index}/{len(cases)}] {case.case_id} {case.category} -> {obs.outcome or 'done'}"
            )
            if stop_reason:
                break
    finally:
        rag_logger.removeHandler(handler)
        rag_logger.setLevel(previous_level)
    return observations, stop_reason
