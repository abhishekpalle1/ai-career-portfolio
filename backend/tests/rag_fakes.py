"""Shared fakes for live-RAG tests. No network, no SDK clients."""

from __future__ import annotations

from pydantic import SecretStr

from app.core.config import Settings
from app.retrieval.vector_store import RetrievedChunk
from app.services.generation import GeneratedAnswer, GeneratedClaim

DUMMY_KEY = "dummy-test-key-not-real-000000"


def live_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "enable_live_model_calls": True,
        "enable_live_rag": True,
        "gemini_api_key": SecretStr(DUMMY_KEY),
        "gemini_embedding_model": "test-embedding-model",
        "gemini_embedding_dimensions": 1536,
        "gemini_generation_model": "test-generation-model",
        "pinecone_api_key": SecretStr(DUMMY_KEY),
        "pinecone_index": "test-index",
        "pinecone_namespace": "test-namespace",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def chunk(
    chunk_id: str,
    score: float,
    *,
    experience_type: str = "PROFESSIONAL",
    section: str = "WORK EXPERIENCE",
    body: str = "- Built a scoring platform ranking 45K claims.",
    content_hash: str | None = None,
    heading_path: str | None = None,
) -> RetrievedChunk:
    path = heading_path or f"ABHISHEK PALLE > {section} > Heading"
    return RetrievedChunk(
        chunk_id=chunk_id,
        score=score,
        content=f"{path}\n\n{body}",
        content_hash=content_hash or f"hash-{chunk_id}",
        source_id="resume-abhishek-palle-current",
        source_name="Resume",
        source_type="RESUME",
        section=section,
        experience_type=experience_type,
        source_url="/resume.pdf",
        heading_path=path,
    )


def answer(
    text: str = "He built a scoring platform ranking 45K claims [C1].",
    *,
    claims: list[GeneratedClaim] | None = None,
    citation_ids: list[str] | None = None,
    grounded: bool = True,
    abstained: bool = False,
    suggestions: list[str] | None = None,
) -> GeneratedAnswer:
    return GeneratedAnswer(
        answer=text,
        claims=claims
        if claims is not None
        else [
            GeneratedClaim(
                text="Built a scoring platform ranking 45K claims",
                citation_ids=["C1"],
                support_level="SUPPORTED",
                experience_type="PROFESSIONAL",
            )
        ],
        citation_ids=citation_ids if citation_ids is not None else ["C1"],
        grounded=grounded,
        abstained=abstained,
        abstention_reason=None if not abstained else "Insufficient evidence",
        suggested_questions=suggestions if suggestions is not None else ["What else did he build?"],
    )


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.1] * 8


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk], error: Exception | None = None) -> None:
        self.chunks = chunks
        self.error = error
        self.calls: list[int] = []

    def retrieve(self, vector: list[float], top_k: int) -> list[RetrievedChunk]:
        self.calls.append(top_k)
        if self.error is not None:
            raise self.error
        return list(self.chunks)


class FakeGenerator:
    def __init__(self, result: GeneratedAnswer | None) -> None:
        self.result = result
        self.calls: list[tuple[str, list[str]]] = []

    def generate(self, question: str, context: list[RetrievedChunk]) -> GeneratedAnswer | None:
        self.calls.append((question, [c.chunk_id for c in context]))
        return self.result
