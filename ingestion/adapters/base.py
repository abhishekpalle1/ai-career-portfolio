from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Protocol, TypeVar

from ingestion.models import VectorRecord

T = TypeVar("T")


class Embedder(Protocol):
    @property
    def model(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    def upsert(self, records: Sequence[VectorRecord]) -> None: ...

    def delete(self, ids: Sequence[str]) -> None: ...


def batched(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
