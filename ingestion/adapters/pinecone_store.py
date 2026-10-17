from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ingestion.adapters.base import batched
from ingestion.config import Settings
from ingestion.models import VectorRecord

UPSERT_BATCH_SIZE = 100
DELETE_BATCH_SIZE = 1000


class PineconeVectorStore:
    def __init__(self, index: Any, namespace: str) -> None:
        self._index = index
        self._namespace = namespace

    @classmethod
    def from_settings(cls, settings: Settings) -> PineconeVectorStore:
        from pinecone import Pinecone

        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required")
        client = Pinecone(api_key=settings.pinecone_api_key)
        return cls(client.Index(settings.pinecone_index), settings.pinecone_namespace)

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        for batch in batched(records, UPSERT_BATCH_SIZE):
            self._index.upsert(
                vectors=[
                    {
                        "id": record.id,
                        "values": record.values,
                        # Pinecone rejects null metadata values.
                        "metadata": {k: v for k, v in record.metadata.items() if v is not None},
                    }
                    for record in batch
                ],
                namespace=self._namespace,
            )

    def delete(self, ids: Sequence[str]) -> None:
        for batch in batched(ids, DELETE_BATCH_SIZE):
            self._index.delete(ids=list(batch), namespace=self._namespace)
