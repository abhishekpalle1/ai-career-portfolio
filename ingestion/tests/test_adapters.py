from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from ingestion.adapters.gemini_embedder import GeminiEmbedder, format_document
from ingestion.adapters.pinecone_store import PineconeVectorStore
from ingestion.models import VectorRecord


class FakeGeminiModels:
    def __init__(self, dimensions: int, drop_last: bool = False) -> None:
        self.dimensions = dimensions
        self.drop_last = drop_last
        self.calls: list[dict[str, Any]] = []

    def embed_content(self, *, model: str, contents: list[Any], config: Any) -> SimpleNamespace:
        self.calls.append({"model": model, "contents": contents, "config": config})
        embeddings = [
            SimpleNamespace(values=[float(i)] * self.dimensions) for i in range(len(contents))
        ]
        return SimpleNamespace(embeddings=embeddings[:-1] if self.drop_last else embeddings)


def test_gemini_embedder_sends_one_content_per_text_with_document_format() -> None:
    models = FakeGeminiModels(dimensions=4)
    embedder = GeminiEmbedder(SimpleNamespace(models=models), "embed-model", 4, batch_size=2)

    vectors = embedder.embed(["a", "bb", "ccc"])

    assert vectors == [[0.0] * 4, [1.0] * 4, [0.0] * 4]
    assert [len(call["contents"]) for call in models.calls] == [2, 1]
    first = models.calls[0]
    assert first["model"] == "embed-model"
    assert first["config"] == {"output_dimensionality": 4}
    assert first["contents"][0] == {"parts": [{"text": "title: none | text: a"}]}
    assert format_document("x") == "title: none | text: x"
    assert embedder.model == "embed-model@4d"


def test_gemini_embedder_rejects_wrong_dimension_or_count() -> None:
    wrong_dims = GeminiEmbedder(SimpleNamespace(models=FakeGeminiModels(3)), "m", 4)
    with pytest.raises(RuntimeError, match="dimension"):
        wrong_dims.embed(["a"])

    missing = GeminiEmbedder(SimpleNamespace(models=FakeGeminiModels(4, drop_last=True)), "m", 4)
    with pytest.raises(RuntimeError, match="count"):
        missing.embed(["a", "b"])


def test_gemini_embedder_requires_complete_settings() -> None:
    from ingestion.config import Settings

    with pytest.raises(ValueError, match="GEMINI_EMBEDDING_DIMENSIONS"):
        GeminiEmbedder.from_settings(
            Settings(embedding_model="gemini-embedding-2", gemini_api_key="dummy")
        )


class FakeIndex:
    def __init__(self) -> None:
        self.upserts: list[tuple[list[dict[str, object]], str]] = []
        self.deletes: list[tuple[list[str], str]] = []

    def upsert(self, *, vectors: list[dict[str, object]], namespace: str) -> None:
        self.upserts.append((vectors, namespace))

    def delete(self, *, ids: list[str], namespace: str) -> None:
        self.deletes.append((ids, namespace))


def test_pinecone_store_batches_drops_null_metadata_and_uses_namespace() -> None:
    index = FakeIndex()
    store = PineconeVectorStore(index, "production")
    records = [
        VectorRecord(id=f"id-{i}", values=[0.5], metadata={"project_id": None, "approved": True})
        for i in range(150)
    ]

    store.upsert(records)
    store.delete(["id-1", "id-2"])

    assert [len(vectors) for vectors, _ in index.upserts] == [100, 50]
    assert {namespace for _, namespace in index.upserts} == {"production"}
    assert index.upserts[0][0][0] == {"id": "id-0", "values": [0.5], "metadata": {"approved": True}}
    assert index.deletes == [(["id-1", "id-2"], "production")]
