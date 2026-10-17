"""Live RAG assistant: one query embedding, one filtered retrieval, one generation call."""

from __future__ import annotations

import logging
import re
import time
import uuid

from app.core.config import Settings
from app.guardrails.cost_controls import AnswerCache
from app.guardrails.input_guard import check_input
from app.guardrails.output_guard import check_output
from app.guardrails.retrieval_guard import filter_unsafe_chunks
from app.models.chat import ChatResponse, Citation, Intent
from app.prompts.grounded_answer import PROMPT_VERSION, citation_id
from app.retrieval.context import select_context
from app.retrieval.embeddings import GeminiQueryEmbedder, QueryEmbedder
from app.retrieval.vector_store import PineconeRetriever, RetrievedChunk, Retriever
from app.services.generation import AnswerGenerator, GeminiAnswerGenerator, GeneratedAnswer
from app.services.intent import classify_intent

logger = logging.getLogger("career-portfolio.rag")

UNAVAILABLE_MESSAGE = (
    "The AI assistant is temporarily unavailable. You can still explore Abhishek's "
    "experience, projects, skills, and resume on this page."
)
OUT_OF_SCOPE_ANSWER = (
    "I'm Abhishek's AI career portfolio assistant. I can answer questions about his "
    "documented professional experience, technical skills, portfolio projects, education, "
    "and role alignment."
)
ABSTENTION_ANSWER = (
    "I couldn't find enough approved evidence to answer that. You can ask about Abhishek's "
    "professional experience, portfolio projects, technical skills, or education."
)
CONTACT_ANSWER = "You can reach Abhishek through the links in the Contact section of this page."
RESUME_ANSWER = "You can open Abhishek's resume from the Resume link on this page."
DEFAULT_SUGGESTIONS = [
    "Where has Abhishek worked?",
    "What production AI systems has he built?",
    "What is his educational background?",
]

EXCERPT_MAX_CHARS = 280
MAX_SUGGESTION_CHARS = 150
_BRACKET_GROUP_RE = re.compile(r"\[([^\[\]]*)\]")
_CITATION_TOKEN_RE = re.compile(r"\bC\s*\d+\b", re.IGNORECASE)
_CITATION_GROUP_RE = re.compile(r"\s*C\d+(?:\s*,\s*C\d+)*\s*")
_CITATION_ID_RE = re.compile(r"C\d+")
# Formatting problems a regeneration could fix; everything else is a hard FAIL.
_REPAIRABLE_VALIDATION = frozenset(
    {"unparsed_output", "malformed_citation_marker", "uncited_answer", "uncited_claim"}
)
_SUGGESTION_UNSAFE_RE = re.compile(r"<|>|\b(?:https?|javascript|data|file)\s*:", re.IGNORECASE)


class AssistantUnavailableError(RuntimeError):
    pass


class RagAssistant:
    def __init__(
        self,
        settings: Settings,
        embedder: QueryEmbedder,
        retriever: Retriever,
        generator: AnswerGenerator,
        cache: AnswerCache | None = None,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._retriever = retriever
        self._generator = generator
        self._cache = cache or AnswerCache(
            ttl_seconds=settings.cache_ttl_seconds, max_entries=settings.cache_max_entries
        )
        self._cache_versions = (
            settings.corpus_version,
            settings.gemini_generation_model,
            settings.gemini_embedding_model,
            str(settings.gemini_embedding_dimensions),
            settings.pinecone_namespace,
            PROMPT_VERSION,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> RagAssistant:
        """Builds clients without any network call; the first request connects."""
        missing = settings.missing_live_rag_settings()
        if missing or settings.gemini_api_key is None:
            raise AssistantUnavailableError(f"Live RAG settings missing: {', '.join(missing)}")
        from google import genai
        from google.genai import types

        # attempts=1: no hidden retries on the request path.
        client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=int(settings.external_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        return cls(
            settings,
            GeminiQueryEmbedder.from_settings(settings, client),
            PineconeRetriever.from_settings(settings),
            GeminiAnswerGenerator.from_settings(settings, client),
        )

    def answer(self, message: str) -> ChatResponse:
        trace_id = uuid.uuid4().hex[:16]
        started = time.perf_counter()

        verdict = check_input(message)
        if not verdict.allowed:
            logger.info("trace=%s outcome=blocked_input category=%s", trace_id, verdict.category)
            return _fixed(OUT_OF_SCOPE_ANSWER, "OUT_OF_SCOPE", trace_id, abstained=True)

        intent = classify_intent(message)
        if intent == "OUT_OF_SCOPE":
            return _fixed(OUT_OF_SCOPE_ANSWER, intent, trace_id, abstained=True)
        if intent == "CONTACT_INFORMATION":
            return _fixed(CONTACT_ANSWER, intent, trace_id, abstained=False)
        if intent == "RESUME_REQUEST":
            return _fixed(RESUME_ANSWER, intent, trace_id, abstained=False)

        question = re.sub(r"\s+", " ", message).strip()
        cache_key = AnswerCache.make_key(question, versions=self._cache_versions)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("trace=%s intent=%s outcome=cache_hit", trace_id, intent)
            return cached.model_copy(update={"trace_id": trace_id})

        settings = self._settings
        attempts = 1 + max(0, settings.max_generation_retries)
        failure: str | None = None
        final_answer = ""
        generated: GeneratedAnswer | None = None
        retrieved: list[RetrievedChunk] = []
        context: list[RetrievedChunk] = []
        dropped = generations = 0
        try:
            vector = self._embedder.embed_query(question)
            retrieved, dropped = filter_unsafe_chunks(
                self._retriever.retrieve(vector, settings.retrieval_top_k)
            )
            context = select_context(
                retrieved,
                final_chunks=settings.final_context_chunks,
                min_score=settings.min_retrieval_score,
                max_context_tokens=settings.max_context_tokens,
            )
            failure = "no_context" if not context else None
            while context and generations < attempts:
                generations += 1
                generated = self._generator.generate(question, context)
                failure, repairable, final_answer = self._evaluate(generated, context)
                if failure is None or not repairable:
                    break
        except Exception as exc:
            # Log only the error type; SDK messages can echo request details.
            logger.error("trace=%s dependency_failure=%s", trace_id, type(exc).__name__)
            raise AssistantUnavailableError("Live RAG dependency failed") from None

        logger.info(
            "trace=%s intent=%s retrieved=%d unsafe_dropped=%d context=%d generations=%d "
            "outcome=%s latency_ms=%d",
            trace_id,
            intent,
            len(retrieved),
            dropped,
            len(context),
            generations,
            failure or "answered",
            (time.perf_counter() - started) * 1000,
        )
        if failure is not None or generated is None:
            return _fixed(ABSTENTION_ANSWER, intent, trace_id, abstained=True)
        response = _grounded_response(generated, final_answer, context, intent, trace_id)
        self._cache.put(cache_key, response)
        return response

    def _evaluate(
        self, generated: GeneratedAnswer | None, context: list[RetrievedChunk]
    ) -> tuple[str | None, bool, str]:
        """Return (failure_reason, repairable, guarded_answer_text)."""
        failure = validate_generated(generated, context)
        if failure is not None or generated is None:
            return failure, failure in _REPAIRABLE_VALIDATION, ""
        guarded = check_output(
            generated.answer.strip(),
            context,
            max_characters=self._settings.max_answer_characters,
        )
        if guarded.verdict == "PASS":
            return None, False, guarded.answer
        return guarded.reason, guarded.verdict == "REPAIRABLE", ""


def parse_inline_citations(answer: str) -> tuple[list[str], bool]:
    """Return unique citation IDs in order of appearance, and whether any marker was malformed.

    Accepts [C1], [C1, C3], and [C1,C3]. Brackets without a citation token (e.g. [sic]) are
    ignored; any other bracket containing a citation token, such as [C1 C3], is malformed.
    """
    ids: list[str] = []
    malformed = False
    for group in _BRACKET_GROUP_RE.findall(answer):
        if not _CITATION_TOKEN_RE.search(group):
            continue
        if not _CITATION_GROUP_RE.fullmatch(group):
            malformed = True
            continue
        for cid in _CITATION_ID_RE.findall(group):
            if cid not in ids:
                ids.append(cid)
    return ids, malformed


def _referenced_ids(generated: GeneratedAnswer) -> set[str]:
    ids = set(generated.citation_ids)
    ids.update(cid for claim in generated.claims for cid in claim.citation_ids)
    ids.update(parse_inline_citations(generated.answer)[0])
    return ids


def validate_generated(
    generated: GeneratedAnswer | None, context: list[RetrievedChunk]
) -> str | None:
    """Return a failure reason, or None when the answer is safe to return."""
    if generated is None:
        return "unparsed_output"
    if generated.abstained or not generated.grounded:
        return "model_abstained"
    if not generated.answer.strip():
        return "empty_answer"
    if parse_inline_citations(generated.answer)[1]:
        return "malformed_citation_marker"
    by_id = {citation_id(i): chunk for i, chunk in enumerate(context, start=1)}
    referenced = _referenced_ids(generated)
    if not referenced or not generated.claims:
        return "uncited_answer"
    if not referenced <= by_id.keys():
        return "unknown_citation"
    for claim in generated.claims:
        if claim.support_level == "UNSUPPORTED":
            return "unsupported_claim"
        if not claim.citation_ids:
            return "uncited_claim"
        cited_types = {by_id[cid].experience_type for cid in claim.citation_ids}
        if claim.experience_type in ("PROFESSIONAL", "PORTFOLIO") and (
            claim.experience_type not in cited_types
        ):
            return "attribution_mismatch"
    return None


def _grounded_response(
    generated: GeneratedAnswer,
    answer_text: str,
    context: list[RetrievedChunk],
    intent: Intent,
    trace_id: str,
) -> ChatResponse:
    referenced = _referenced_ids(generated)
    citations = [
        _to_citation(citation_id(i), chunk)
        for i, chunk in enumerate(context, start=1)
        if citation_id(i) in referenced
    ]
    return ChatResponse(
        answer=answer_text,
        citations=citations,
        suggested_questions=_clean_suggestions(generated.suggested_questions),
        intent=intent,
        grounded=True,
        abstained=False,
        trace_id=trace_id,
    )


def _to_citation(cid: str, chunk: RetrievedChunk) -> Citation:
    return Citation.model_validate(
        {
            "citation_id": cid,
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_name": chunk.source_name,
            "source_type": chunk.source_type,
            "section": chunk.section,
            "experience_type": chunk.experience_type,
            "source_url": chunk.source_url,
            "excerpt": make_excerpt(chunk.content),
        }
    )


def make_excerpt(content: str) -> str:
    """Bounded excerpt of the chunk body (heading path removed)."""
    body = " ".join(content.split("\n\n", 1)[-1].split())
    if len(body) <= EXCERPT_MAX_CHARS:
        return body
    cut = body[:EXCERPT_MAX_CHARS].rsplit(" ", 1)[0]
    return f"{cut}…"


def _clean_suggestions(suggestions: list[str]) -> list[str]:
    cleaned: list[str] = []
    for suggestion in suggestions:
        text = " ".join(suggestion.split())
        if (
            text
            and len(text) <= MAX_SUGGESTION_CHARS
            and text not in cleaned
            and not _SUGGESTION_UNSAFE_RE.search(text)
            and check_input(text).allowed
        ):
            cleaned.append(text)
    return cleaned[:3] or list(DEFAULT_SUGGESTIONS)


def _fixed(answer: str, intent: Intent, trace_id: str, *, abstained: bool) -> ChatResponse:
    return ChatResponse(
        answer=answer,
        citations=[],
        suggested_questions=list(DEFAULT_SUGGESTIONS),
        intent=intent,
        grounded=False,
        abstained=abstained,
        trace_id=trace_id,
    )
