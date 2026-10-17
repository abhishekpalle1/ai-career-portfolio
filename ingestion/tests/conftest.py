from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
import yaml

from ingestion.config import Settings
from ingestion.models import VectorRecord

LIVE_ENV_VARS = (
    "ENABLE_LIVE_MODEL_CALLS",
    "OPENAI_API_KEY",
    "OPENAI_EMBEDDING_MODEL",
    "PINECONE_API_KEY",
    "PINECONE_INDEX",
    "PINECONE_NAMESPACE",
    "CHUNK_SIZE_TOKENS",
    "CHUNK_OVERLAP_TOKENS",
)

SAMPLE_BODY = """# Jane Example

## SUMMARY

ML engineer focused on production systems.

## WORK EXPERIENCE

### Acme Corp, ML Engineer | 2020 - Present

#### Fraud Platform

- Built a scoring platform ranking 45K claims.
- Improved precision 23% -> 40% and F1 0.34 -> 0.52.

## SELECTED PROJECTS

### Demo Assistant

- Built a RAG app with citation validation.
"""


def document_text(body: str = SAMPLE_BODY, **overrides: object) -> str:
    fields: dict[str, object] = {
        "source_id": "resume-test",
        "source_type": "RESUME",
        "source_name": "Resume",
        "section": "Full Resume",
        "project_id": None,
        "experience_type": "GENERAL",
        "visibility": "PUBLIC",
        "approved": True,
        "source_url": "/resume.pdf",
        "document_version": "2026-10",
        "updated_at": "2026-10-16",
        "section_experience_types": {
            "WORK EXPERIENCE": "PROFESSIONAL",
            "SELECTED PROJECTS": "PORTFOLIO",
        },
    }
    fields.update(overrides)
    front_matter = yaml.safe_dump(fields, sort_keys=False)
    return f"---\n{front_matter}---\n\n{body}"


@pytest.fixture
def kb_dir(tmp_path: Path) -> Path:
    path = tmp_path / "knowledge-base"
    path.mkdir()
    return path


@pytest.fixture
def write_doc(kb_dir: Path) -> Callable[..., Path]:
    def write(relative_path: str, body: str = SAMPLE_BODY, **overrides: object) -> Path:
        path = kb_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document_text(body, **overrides), encoding="utf-8")
        return path

    return write


@pytest.fixture
def settings() -> Settings:
    return Settings(embedding_model="test-embedding-model")


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in LIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class FakeEmbedder:
    def __init__(self, model: str = "test-embedding-model") -> None:
        self._model = model
        self.calls: list[list[str]] = []

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(len(text)), 1.0] for text in texts]


class FakeStore:
    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}
        self.upsert_calls = 0
        self.deleted: list[str] = []

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        self.upsert_calls += 1
        for record in records:
            self.records[record.id] = record

    def delete(self, ids: Sequence[str]) -> None:
        self.deleted.extend(ids)
        for record_id in ids:
            self.records.pop(record_id, None)
