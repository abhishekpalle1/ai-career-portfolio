from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings

logger = logging.getLogger("career-portfolio.retrieval")

# Applied by backend code on every query; never derived from user or model input.
MANDATORY_FILTER: dict[str, Any] = {
    "visibility": {"$eq": "PUBLIC"},
    "approved": {"$eq": True},
    "ingestion_status": {"$eq": "VERIFIED"},
}

SOURCE_TYPES = frozenset(
    {
        "RESUME",
        "PROFESSIONAL_PROFILE",
        "PROFESSIONAL_EXPERIENCE",
        "PORTFOLIO_PROJECT",
        "SKILLS_EVIDENCE",
        "EDUCATION",
        "CERTIFICATION",
        "RECRUITER_FAQ",
        "PUBLIC_CONTACT",
    }
)
EXPERIENCE_TYPES = frozenset({"PROFESSIONAL", "PORTFOLIO", "EDUCATION", "GENERAL"})
_REQUIRED_TEXT_FIELDS = (
    "content",
    "source_id",
    "source_name",
    "source_type",
    "section",
    "experience_type",
    "source_url",
)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    score: float
    content: str
    content_hash: str
    source_id: str
    source_name: str
    source_type: str
    section: str
    experience_type: str
    source_url: str
    heading_path: str = ""


class Retriever(Protocol):
    def retrieve(self, vector: list[float], top_k: int) -> list[RetrievedChunk]: ...


def is_safe_source_url(url: str) -> bool:
    return (url.startswith("/") and not url.startswith("//")) or url.startswith("https://")


def parse_match(
    chunk_id: str, score: float, metadata: Mapping[str, Any] | None
) -> RetrievedChunk | None:
    """Re-verify the mandatory filter and provenance; drop anything that does not qualify."""
    if not metadata:
        return None
    if (
        metadata.get("visibility") != "PUBLIC"
        or metadata.get("approved") is not True
        or metadata.get("ingestion_status") != "VERIFIED"
    ):
        return None
    if not all(
        isinstance(metadata.get(name), str) and metadata[name] for name in _REQUIRED_TEXT_FIELDS
    ):
        return None
    if (
        metadata["source_type"] not in SOURCE_TYPES
        or metadata["experience_type"] not in EXPERIENCE_TYPES
    ):
        return None
    if not is_safe_source_url(metadata["source_url"]):
        return None
    return RetrievedChunk(
        chunk_id=chunk_id,
        score=float(score),
        content=metadata["content"],
        content_hash=str(metadata.get("content_hash", "")),
        source_id=metadata["source_id"],
        source_name=metadata["source_name"],
        source_type=metadata["source_type"],
        section=metadata["section"],
        experience_type=metadata["experience_type"],
        source_url=metadata["source_url"],
        heading_path=str(metadata.get("heading_path") or ""),
    )


class PineconeRetriever:
    def __init__(self, index: Any, namespace: str, timeout_seconds: float) -> None:
        self._index = index
        self._namespace = namespace
        self._timeout = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> PineconeRetriever:
        from pinecone import Pinecone

        if settings.pinecone_api_key is None:
            raise ValueError("PINECONE_API_KEY is required")
        client = Pinecone(api_key=settings.pinecone_api_key.get_secret_value())
        index = _LazyIndex(client, settings.pinecone_index)
        return cls(index, settings.pinecone_namespace, settings.external_timeout_seconds)

    def retrieve(self, vector: list[float], top_k: int) -> list[RetrievedChunk]:
        response = self._index.query(
            vector=vector,
            top_k=top_k,
            namespace=self._namespace,
            filter=MANDATORY_FILTER,
            include_metadata=True,
            include_values=False,
            timeout=self._timeout,
        )
        chunks: list[RetrievedChunk] = []
        rejected = 0
        for match in response.matches:
            parsed = parse_match(match.id, match.score, match.metadata)
            if parsed is None:
                rejected += 1
            else:
                chunks.append(parsed)
        if rejected:
            logger.warning("Dropped %d retrieved matches that failed provenance checks", rejected)
        return chunks


class _LazyIndex:
    """Defers host lookup (a network call) until the first query."""

    def __init__(self, client: Any, name: str) -> None:
        self._client = client
        self._name = name
        self._index: Any = None

    def query(self, **kwargs: Any) -> Any:
        if self._index is None:
            self._index = self._client.Index(self._name)
        return self._index.query(**kwargs)
