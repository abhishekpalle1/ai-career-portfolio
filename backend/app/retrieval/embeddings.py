from __future__ import annotations

from typing import Any, Protocol

from app.core.config import Settings


class QueryEmbedder(Protocol):
    def embed_query(self, text: str) -> list[float]: ...


def format_query(text: str) -> str:
    """gemini-embedding-2 retrieval query format; ingestion formats documents to match."""
    return f"task: search result | query: {text}"


class GeminiQueryEmbedder:
    """Must use the same model and dimensions as ingestion, or vectors will not match."""

    def __init__(self, client: Any, model: str, dimensions: int) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions

    @classmethod
    def from_settings(cls, settings: Settings, client: Any) -> GeminiQueryEmbedder:
        if settings.gemini_embedding_dimensions is None:
            raise ValueError("GEMINI_EMBEDDING_DIMENSIONS is required")
        return cls(client, settings.gemini_embedding_model, settings.gemini_embedding_dimensions)

    def embed_query(self, text: str) -> list[float]:
        response = self._client.models.embed_content(
            model=self._model,
            contents=[{"parts": [{"text": format_query(text)}]}],
            config={"output_dimensionality": self._dimensions},
        )
        vector = [float(value) for value in response.embeddings[0].values]
        if len(vector) != self._dimensions:
            raise RuntimeError("Query embedding dimension does not match configuration")
        return vector
