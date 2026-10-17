from types import SimpleNamespace
from typing import Any

import pytest

from app.retrieval.context import count_tokens, select_context
from app.retrieval.embeddings import GeminiQueryEmbedder, format_query
from app.retrieval.vector_store import MANDATORY_FILTER, PineconeRetriever, parse_match
from tests.rag_fakes import chunk


def metadata(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "content": "ABHISHEK PALLE > SUMMARY\n\nSenior ML/AI Engineer.",
        "content_hash": "abc",
        "source_id": "resume-abhishek-palle-current",
        "source_name": "Resume",
        "source_type": "RESUME",
        "section": "SUMMARY",
        "experience_type": "GENERAL",
        "source_url": "/resume.pdf",
        "visibility": "PUBLIC",
        "approved": True,
        "ingestion_status": "VERIFIED",
    }
    values.update(overrides)
    return values


def test_parse_match_accepts_verified_public_chunks() -> None:
    parsed = parse_match("id-1", 0.8, metadata())

    assert parsed is not None
    assert parsed.chunk_id == "id-1"
    assert parsed.score == 0.8


@pytest.mark.parametrize(
    "overrides",
    [
        {"visibility": "PRIVATE"},
        {"approved": False},
        {"approved": "true"},
        {"ingestion_status": "PENDING"},
        {"content": ""},
        {"source_name": None},
        {"source_type": "BLOG"},
        {"experience_type": "HOBBY"},
        {"source_url": "javascript:alert(1)"},
        {"source_url": "http://insecure.example"},
        {"source_url": "//evil.example"},
    ],
)
def test_parse_match_rejects_unqualified_chunks(overrides: dict[str, Any]) -> None:
    assert parse_match("id-1", 0.8, metadata(**overrides)) is None


def test_parse_match_rejects_missing_metadata() -> None:
    assert parse_match("id-1", 0.8, None) is None


class FakeIndex:
    def __init__(self, matches: list[SimpleNamespace]) -> None:
        self.matches = matches
        self.calls: list[dict[str, Any]] = []

    def query(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(matches=self.matches)


def test_retriever_always_applies_mandatory_filter_and_drops_bad_matches() -> None:
    index = FakeIndex(
        [
            SimpleNamespace(id="good", score=0.9, metadata=metadata()),
            SimpleNamespace(id="bad", score=0.95, metadata=metadata(approved=False)),
        ]
    )
    retriever = PineconeRetriever(index, "production", timeout_seconds=7.0)

    results = retriever.retrieve([0.1, 0.2], top_k=12)

    assert [r.chunk_id for r in results] == ["good"]
    call = index.calls[0]
    assert call["filter"] == MANDATORY_FILTER
    assert call["filter"] == {
        "visibility": {"$eq": "PUBLIC"},
        "approved": {"$eq": True},
        "ingestion_status": {"$eq": "VERIFIED"},
    }
    assert call["namespace"] == "production"
    assert call["top_k"] == 12
    assert call["include_metadata"] is True
    assert call["include_values"] is False
    assert call["timeout"] == 7.0


def test_select_context_orders_dedupes_and_limits() -> None:
    chunks = [
        chunk("low", 0.2),
        chunk("high", 0.9),
        chunk("dup-of-high", 0.85, content_hash="hash-high"),
        chunk("mid", 0.5),
        chunk("mid2", 0.4),
    ]

    selected = select_context(chunks, final_chunks=3, min_score=None, max_context_tokens=None)

    assert [c.chunk_id for c in selected] == ["high", "mid", "mid2"]


def test_select_context_applies_min_score_and_token_budget() -> None:
    chunks = [chunk("a", 0.9), chunk("b", 0.8), chunk("c", 0.1)]

    assert [
        c.chunk_id
        for c in select_context(chunks, final_chunks=5, min_score=0.5, max_context_tokens=None)
    ] == ["a", "b"]
    one_chunk_budget = count_tokens(chunks[0].content) + 5
    budgeted = select_context(
        chunks, final_chunks=5, min_score=None, max_context_tokens=one_chunk_budget
    )
    assert [c.chunk_id for c in budgeted] == ["a"]


class FakeGeminiModels:
    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self.calls: list[dict[str, Any]] = []

    def embed_content(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1] * self.dimensions)])


def test_gemini_query_embedder_uses_query_format_and_dimensions() -> None:
    models = FakeGeminiModels(dimensions=3)
    embedder = GeminiQueryEmbedder(SimpleNamespace(models=models), "embed-model", 3)

    assert embedder.embed_query("question") == [1.0, 1.0, 1.0]
    call = models.calls[0]
    assert call["model"] == "embed-model"
    assert call["contents"] == [{"parts": [{"text": "task: search result | query: question"}]}]
    assert call["config"] == {"output_dimensionality": 3}
    assert format_query("x") == "task: search result | query: x"


def test_gemini_query_embedder_rejects_dimension_mismatch() -> None:
    embedder = GeminiQueryEmbedder(SimpleNamespace(models=FakeGeminiModels(2)), "m", 3)

    with pytest.raises(RuntimeError, match="dimension"):
        embedder.embed_query("question")
