from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ingestion.adapters.base import batched
from ingestion.config import Settings

REQUEST_TIMEOUT_SECONDS = 30.0


class OpenAIEmbedder:
    """Document embeddings. The backend must embed queries with the same model and dimensions."""

    def __init__(
        self, client: Any, model: str, dimensions: int | None = None, batch_size: int = 64
    ) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenAIEmbedder:
        from openai import OpenAI

        if not settings.openai_api_key or not settings.embedding_model:
            raise ValueError("OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL are required")
        # No hidden retries: the operator re-runs; the manifest keeps re-runs idempotent.
        client = OpenAI(
            api_key=settings.openai_api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0
        )
        return cls(client, settings.embedding_model, settings.embedding_dimensions)

    @property
    def model(self) -> str:
        """Embedding identity recorded in the manifest (model plus dimensions)."""
        if self._dimensions is None:
            return self._model
        return f"{self._model}@{self._dimensions}d"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(texts, self._batch_size):
            kwargs: dict[str, Any] = {"model": self._model, "input": list(batch)}
            if self._dimensions is not None:
                kwargs["dimensions"] = self._dimensions
            response = self._client.embeddings.create(**kwargs)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([float(value) for value in item.embedding] for item in ordered)
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding count does not match input count")
        return vectors
