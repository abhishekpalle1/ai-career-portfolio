from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ingestion.adapters.base import batched
from ingestion.config import Settings

REQUEST_TIMEOUT_SECONDS = 30.0


class OpenAIEmbedder:
    """Document embeddings. Phase 3 must embed queries with the same model."""

    def __init__(self, client: Any, model: str, batch_size: int = 64) -> None:
        self._client = client
        self._model = model
        self._batch_size = batch_size

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAIEmbedder:
        from openai import OpenAI

        if not settings.openai_api_key or not settings.embedding_model:
            raise ValueError("OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL are required")
        client = OpenAI(
            api_key=settings.openai_api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=2
        )
        return cls(client, settings.embedding_model)

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(texts, self._batch_size):
            response = self._client.embeddings.create(model=self._model, input=list(batch))
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([float(value) for value in item.embedding] for item in ordered)
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding count does not match input count")
        return vectors
