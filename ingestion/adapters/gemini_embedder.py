from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ingestion.adapters.base import batched
from ingestion.config import Settings

REQUEST_TIMEOUT_MS = 30_000
BATCH_SIZE = 50


def format_document(text: str) -> str:
    """gemini-embedding-2 takes the task in the text; the backend formats queries to match."""
    return f"title: none | text: {text}"


class GeminiEmbedder:
    """Document embeddings. The backend must embed queries with the same model and dimensions."""

    def __init__(
        self, client: Any, model: str, dimensions: int, batch_size: int = BATCH_SIZE
    ) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    @classmethod
    def from_settings(cls, settings: Settings) -> GeminiEmbedder:
        from google import genai
        from google.genai import types

        if (
            not settings.gemini_api_key
            or not settings.embedding_model
            or settings.embedding_dimensions is None
        ):
            raise ValueError(
                "GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL, and GEMINI_EMBEDDING_DIMENSIONS "
                "are required"
            )
        # No hidden retries: the operator re-runs; the manifest keeps re-runs idempotent.
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        return cls(client, settings.embedding_model, settings.embedding_dimensions)

    @property
    def model(self) -> str:
        """Embedding identity recorded in the manifest (model plus dimensions)."""
        return f"{self._model}@{self._dimensions}d"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(texts, self._batch_size):
            # One Content per text: a plain list would be aggregated into a single embedding.
            response = self._client.models.embed_content(
                model=self._model,
                contents=[{"parts": [{"text": format_document(text)}]} for text in batch],
                config={"output_dimensionality": self._dimensions},
            )
            batch_vectors = [[float(v) for v in item.values] for item in response.embeddings]
            if len(batch_vectors) != len(batch):
                raise RuntimeError("Embedding count does not match input count")
            if any(len(vector) != self._dimensions for vector in batch_vectors):
                raise RuntimeError("Embedding dimension does not match GEMINI_EMBEDDING_DIMENSIONS")
            vectors.extend(batch_vectors)
        return vectors
