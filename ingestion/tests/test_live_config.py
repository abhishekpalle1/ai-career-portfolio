"""Phase 3 ingestion configuration: env files, upsert gate, embedding dimensions, preflight."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ingestion.adapters.gemini_embedder import GeminiEmbedder
from ingestion.adapters.pinecone_store import PineconeVectorStore
from ingestion.cli import main
from ingestion.config import ConfigError, Settings, load_env_file
from ingestion.pipelines.ingest import run_ingestion
from ingestion.tests.conftest import FakeEmbedder, FakeStore

WriteDoc = Callable[..., Path]
DUMMY_KEY = "dummy-test-key-not-real-000000"


def env_file(tmp_path: Path, **values: str) -> Path:
    path = tmp_path / "test.env"
    path.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
    return path


def test_load_env_file_parses_comments_exports_quotes_and_duplicates(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "# comment\n\nexport A=1\nB=\"two\"\nC='three'\nA=4\nNOT_A_PAIR\n", encoding="utf-8"
    )

    assert load_env_file(path) == {"A": "4", "B": "two", "C": "three"}


def test_load_env_file_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_env_file(tmp_path / "missing.env")


def test_settings_parse_dimensions_and_upsert_flag() -> None:
    settings = Settings.from_env(
        {
            "GEMINI_EMBEDDING_MODEL": "embed-model",
            "GEMINI_EMBEDDING_DIMENSIONS": "512",
            "ENABLE_LIVE_VECTOR_UPSERTS": "true",
        }
    )

    assert settings.embedding_dimensions == 512
    assert settings.enable_live_upserts is True
    assert settings.embedding_identity == "embed-model@512d"
    assert Settings(embedding_model="m").embedding_identity == "m"
    assert Settings().embedding_identity is None


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_invalid_dimensions_are_rejected(value: str) -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({"GEMINI_EMBEDDING_DIMENSIONS": value})


def test_apply_requires_both_live_flags() -> None:
    base = {
        "GEMINI_API_KEY": DUMMY_KEY,
        "PINECONE_API_KEY": DUMMY_KEY,
        "GEMINI_EMBEDDING_MODEL": "m",
        "GEMINI_EMBEDDING_DIMENSIONS": "1536",
    }

    only_model = Settings.from_env({**base, "ENABLE_LIVE_MODEL_CALLS": "true"})
    both = Settings.from_env(
        {**base, "ENABLE_LIVE_MODEL_CALLS": "true", "ENABLE_LIVE_VECTOR_UPSERTS": "true"}
    )

    assert only_model.missing_live_requirements() == ["ENABLE_LIVE_VECTOR_UPSERTS=true"]
    assert both.missing_live_requirements() == []
    assert DUMMY_KEY not in repr(both)


def test_apply_requires_gemini_embedding_dimensions() -> None:
    settings = Settings.from_env(
        {
            "GEMINI_API_KEY": DUMMY_KEY,
            "PINECONE_API_KEY": DUMMY_KEY,
            "GEMINI_EMBEDDING_MODEL": "m",
            "ENABLE_LIVE_MODEL_CALLS": "true",
            "ENABLE_LIVE_VECTOR_UPSERTS": "true",
        }
    )

    assert settings.missing_live_requirements() == ["GEMINI_EMBEDDING_DIMENSIONS"]


def test_openai_settings_are_no_longer_read() -> None:
    settings = Settings.from_env(
        {"OPENAI_API_KEY": DUMMY_KEY, "OPENAI_EMBEDDING_MODEL": "m", "PINECONE_API_KEY": "p"}
    )

    assert settings.gemini_api_key is None
    assert settings.embedding_model is None


def test_dimension_change_forces_full_reindex(
    kb_dir: Path, write_doc: WriteDoc, tmp_path: Path
) -> None:
    write_doc("resume.md")
    manifest = tmp_path / "manifest.json"
    store = FakeStore()
    first = Settings(embedding_model="m", embedding_dimensions=512)
    run_ingestion(
        kb_dir,
        first,
        manifest_path=manifest,
        apply=True,
        embedder=FakeEmbedder("m@512d"),
        store=store,
    )

    changed = run_ingestion(
        kb_dir, Settings(embedding_model="m", embedding_dimensions=256), manifest_path=manifest
    )

    assert changed.plan is not None
    assert len(changed.plan.changed) == 3


@pytest.fixture
def no_live_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("live adapter constructed")

    monkeypatch.setattr(GeminiEmbedder, "from_settings", classmethod(refuse))
    monkeypatch.setattr(PineconeVectorStore, "from_settings", classmethod(refuse))


@pytest.mark.usefixtures("no_live_adapters")
def test_cli_env_file_keeps_apply_gated_and_values_hidden(
    kb_dir: Path, write_doc: WriteDoc, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md")
    path = env_file(
        tmp_path,
        ENABLE_LIVE_MODEL_CALLS="true",
        ENABLE_LIVE_VECTOR_UPSERTS="false",
        GEMINI_API_KEY=DUMMY_KEY,
        PINECONE_API_KEY=DUMMY_KEY,
        GEMINI_EMBEDDING_MODEL="embed-model",
        GEMINI_EMBEDDING_DIMENSIONS="1536",
    )
    args = [
        "--kb-dir",
        str(kb_dir),
        "--manifest",
        str(tmp_path / "m.json"),
        "--env-file",
        str(path),
    ]

    assert main([*args, "ingest", "--apply"]) == 2
    captured = capsys.readouterr()
    assert "ENABLE_LIVE_VECTOR_UPSERTS=true" in captured.err
    assert DUMMY_KEY not in captured.out + captured.err


def test_process_environment_overrides_env_file(
    kb_dir: Path,
    write_doc: WriteDoc,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_doc("resume.md")
    path = env_file(tmp_path, CHUNK_SIZE_TOKENS="100", CHUNK_OVERLAP_TOKENS="100")
    assert main(["--kb-dir", str(kb_dir), "--env-file", str(path), "validate"]) == 2

    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "10")
    assert main(["--kb-dir", str(kb_dir), "--env-file", str(path), "validate"]) == 0
    capsys.readouterr()


@pytest.mark.usefixtures("no_live_adapters")
def test_preflight_is_offline_writes_nothing_and_hides_values(
    kb_dir: Path, write_doc: WriteDoc, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md")
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "out"
    path = env_file(
        tmp_path,
        ENABLE_LIVE_MODEL_CALLS="false",
        GEMINI_API_KEY=DUMMY_KEY,
        PINECONE_API_KEY=DUMMY_KEY,
        GEMINI_EMBEDDING_MODEL="embed-model",
        GEMINI_EMBEDDING_DIMENSIONS="512",
    )
    path.write_text(
        path.read_text(encoding="utf-8") + "ENABLE_LIVE_MODEL_CALLS=false\n", encoding="utf-8"
    )
    before = sorted(p.name for p in tmp_path.iterdir())

    code = main(
        [
            "--kb-dir",
            str(kb_dir),
            "--manifest",
            str(state_dir / "manifest.json"),
            "--output-dir",
            str(output_dir),
            "--env-file",
            str(path),
            "preflight",
        ]
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "Corpus: 1 document(s), 3 chunk(s)" in out
    assert "Apply plan vs production manifest: 3 new" in out
    assert (
        "Flags still required for --apply: "
        "ENABLE_LIVE_MODEL_CALLS=true, ENABLE_LIVE_VECTOR_UPSERTS=true" in out
    )
    assert "Duplicate keys in env file (last value wins): ENABLE_LIVE_MODEL_CALLS" in out
    assert "Network attempts blocked: 0" in out
    assert "Result: READY" in out
    assert DUMMY_KEY not in out
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_preflight_reports_missing_keys(
    kb_dir: Path, write_doc: WriteDoc, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md")

    code = main(["--kb-dir", str(kb_dir), "--manifest", str(tmp_path / "m.json"), "preflight"])

    out = capsys.readouterr().out
    assert code == 1
    assert "PROBLEM: GEMINI_API_KEY is not set" in out
    assert "PROBLEM: GEMINI_EMBEDDING_DIMENSIONS is not set" in out
    assert "PROBLEM: PINECONE_API_KEY is not set" in out
    assert "Result: NOT READY" in out
