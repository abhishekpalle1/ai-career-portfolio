"""Live --apply failure path: no retries, no upsert, no manifest, sanitized output only."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from ingestion.adapters.gemini_embedder import GeminiEmbedder
from ingestion.adapters.pinecone_store import PineconeVectorStore
from ingestion.cli import main, sanitized_error
from ingestion.config import Settings
from ingestion.tests.conftest import FakeStore

WriteDoc = Callable[..., Path]
SECRET = "dummy-secret-not-real-000000"  # noqa: S105 - synthetic test value


class QuotaError(Exception):
    """Shaped like google.genai.errors.APIError: `code` is the HTTP status."""

    def __init__(self) -> None:
        super().__init__(f"quota exceeded for key {SECRET} payload=chunk text")
        self.code = 429
        self.status = "RESOURCE_EXHAUSTED"


class FailingEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def model(self) -> str:
        return "m"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        raise QuotaError()


def test_sanitized_error_keeps_only_safe_identifiers() -> None:
    assert sanitized_error(QuotaError()) == (
        "QuotaError http_status=429 provider_code=RESOURCE_EXHAUSTED"
    )
    unsafe = QuotaError()
    unsafe.status = "bad code <script>"
    assert "provider_code=None" in sanitized_error(unsafe)


def test_sanitized_error_handles_status_code_and_integer_status_shapes() -> None:
    status_code_style = Exception()
    status_code_style.status_code = 403  # type: ignore[attr-defined]
    status_code_style.code = "forbidden"  # type: ignore[attr-defined]
    integer_status_style = Exception()
    integer_status_style.status = 404  # type: ignore[attr-defined]

    assert "http_status=403 provider_code=forbidden" in sanitized_error(status_code_style)
    assert "http_status=404 provider_code=None" in sanitized_error(integer_status_style)


def test_quota_failure_stops_before_upsert_and_manifest(
    kb_dir: Path,
    write_doc: WriteDoc,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_doc("resume.md")
    embedder, store = FailingEmbedder(), FakeStore()
    monkeypatch.setattr(GeminiEmbedder, "from_settings", classmethod(lambda cls, s: embedder))
    monkeypatch.setattr(PineconeVectorStore, "from_settings", classmethod(lambda cls, s: store))
    for name, value in {
        "ENABLE_LIVE_MODEL_CALLS": "true",
        "ENABLE_LIVE_VECTOR_UPSERTS": "true",
        "GEMINI_API_KEY": SECRET,
        "PINECONE_API_KEY": SECRET,
        "GEMINI_EMBEDDING_MODEL": "m",
        "GEMINI_EMBEDDING_DIMENSIONS": "1536",
        "PINECONE_NAMESPACE": "development",
    }.items():
        monkeypatch.setenv(name, value)
    manifest = tmp_path / "manifest.json"
    output_dir = tmp_path / "out"

    code = main(
        [
            "--kb-dir",
            str(kb_dir),
            "--manifest",
            str(manifest),
            "--output-dir",
            str(output_dir),
            "ingest",
            "--apply",
        ]
    )

    captured = capsys.readouterr()
    assert code == 1
    assert embedder.calls == 1
    assert store.upsert_calls == 0
    assert not manifest.exists()
    assert not output_dir.exists()
    assert "namespace=development" in captured.out
    assert "http_status=429 provider_code=RESOURCE_EXHAUSTED" in captured.err
    assert SECRET not in captured.out + captured.err
    assert "chunk text" not in captured.out + captured.err


def test_gemini_client_is_built_without_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    genai = pytest.importorskip("google.genai")
    captured: dict[str, object] = {}

    def fake_client(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(genai, "Client", fake_client)
    settings = Settings(
        embedding_model="gemini-embedding-2", embedding_dimensions=1536, gemini_api_key=SECRET
    )

    GeminiEmbedder.from_settings(settings)

    http_options = captured["http_options"]
    assert http_options.retry_options.attempts == 1  # type: ignore[attr-defined]
    assert captured["api_key"] == SECRET
