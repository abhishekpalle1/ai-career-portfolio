from __future__ import annotations

from types import SimpleNamespace

from ingestion.adapters.openai_embedder import OpenAIEmbedder
from ingestion.adapters.pinecone_store import PineconeVectorStore
from ingestion.models import VectorRecord


class FakeEmbeddingsAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def create(self, *, model: str, input: list[str]) -> SimpleNamespace:
        self.calls.append((model, input))
        data = [
            SimpleNamespace(index=i, embedding=[float(i), float(len(text))])
            for i, text in enumerate(input)
        ]
        return SimpleNamespace(data=list(reversed(data)))


class FakeIndex:
    def __init__(self) -> None:
        self.upserts: list[tuple[list[dict[str, object]], str]] = []
        self.deletes: list[tuple[list[str], str]] = []

    def upsert(self, *, vectors: list[dict[str, object]], namespace: str) -> None:
        self.upserts.append((vectors, namespace))

    def delete(self, *, ids: list[str], namespace: str) -> None:
        self.deletes.append((ids, namespace))


def test_openai_embedder_batches_and_restores_input_order() -> None:
    api = FakeEmbeddingsAPI()
    embedder = OpenAIEmbedder(SimpleNamespace(embeddings=api), "embed-model", batch_size=2)

    vectors = embedder.embed(["a", "bb", "ccc"])

    assert vectors == [[0.0, 1.0], [1.0, 2.0], [0.0, 3.0]]
    assert [(model, len(batch)) for model, batch in api.calls] == [
        ("embed-model", 2),
        ("embed-model", 1),
    ]
    assert embedder.model == "embed-model"


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
