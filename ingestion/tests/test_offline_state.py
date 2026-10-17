"""Offline stateful runs: persisted change detection with no embedding or vector-store calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from ingestion.adapters.gemini_embedder import GeminiEmbedder
from ingestion.adapters.pinecone_store import PineconeVectorStore
from ingestion.cli import main
from ingestion.config import DEFAULT_MANIFEST_PATH, Settings
from ingestion.pipelines.ingest import IngestionError, run_ingestion
from ingestion.pipelines.manifest import load_manifest
from ingestion.tests.conftest import SAMPLE_BODY, FakeEmbedder, FakeStore

WriteDoc = Callable[..., Path]


@pytest.fixture
def no_live_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("live adapter constructed during an offline run")

    monkeypatch.setattr(GeminiEmbedder, "from_settings", classmethod(refuse))
    monkeypatch.setattr(PineconeVectorStore, "from_settings", classmethod(refuse))


def test_offline_runs_detect_new_then_unchanged_then_changed(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, tmp_path: Path
) -> None:
    write_doc("resume.md")
    manifest_path = tmp_path / "state" / "manifest.json"

    first = run_ingestion(kb_dir, settings, manifest_path=manifest_path, persist_manifest=True)
    assert first.plan is not None
    assert (len(first.plan.new), len(first.plan.unchanged)) == (3, 0)
    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert manifest.offline is True

    second = run_ingestion(kb_dir, settings, manifest_path=manifest_path, persist_manifest=True)
    assert second.plan is not None
    assert (len(second.plan.new), len(second.plan.unchanged)) == (0, 3)
    assert second.embedded == second.upserted == second.deleted == 0

    write_doc("resume.md", SAMPLE_BODY.replace("45K", "46K"))
    third = run_ingestion(kb_dir, settings, manifest_path=manifest_path, persist_manifest=True)
    assert third.plan is not None
    assert (len(third.plan.changed), len(third.plan.unchanged)) == (1, 2)


def test_apply_ignores_offline_manifest(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, tmp_path: Path
) -> None:
    write_doc("resume.md")
    manifest_path = tmp_path / "manifest.json"
    run_ingestion(kb_dir, settings, manifest_path=manifest_path, persist_manifest=True)
    store = FakeStore()

    result = run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    assert result.plan is not None
    assert len(result.plan.new) == 3
    assert len(store.records) == 3
    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert manifest.offline is False


def test_offline_persist_refuses_invalid_corpus_and_apply_combination(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, tmp_path: Path
) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_doc("resume.md", SAMPLE_BODY + "\nCall 555-010-0199\n")

    with pytest.raises(IngestionError):
        run_ingestion(kb_dir, settings, manifest_path=manifest_path, persist_manifest=True)
    with pytest.raises(IngestionError):
        run_ingestion(
            kb_dir, settings, manifest_path=manifest_path, apply=True, persist_manifest=True
        )
    assert not manifest_path.exists()


@pytest.mark.usefixtures("no_live_adapters")
def test_cli_offline_persist_never_goes_live_even_with_live_env(
    kb_dir: Path,
    write_doc: WriteDoc,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_doc("resume.md")
    monkeypatch.setenv("ENABLE_LIVE_MODEL_CALLS", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-gemini-key-000000000000")
    monkeypatch.setenv("PINECONE_API_KEY", "not-a-real-key")
    manifest_path = tmp_path / "state" / "manifest.json"
    output_dir = tmp_path / "out"
    args = [
        "--kb-dir",
        str(kb_dir),
        "--manifest",
        str(manifest_path),
        "--output-dir",
        str(output_dir),
        "ingest",
        "--persist-manifest",
    ]

    assert main(args) == 0
    assert main(args) == 0
    assert "Plan: 0 new, 0 changed, 3 unchanged, 0 stale" in capsys.readouterr().out
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["mode"] == "offline-persist"
    assert report["live_services_used"] is False
    assert report["actions"] == {"embedded": 0, "upserted": 0, "deleted": 0}


def test_cli_offline_persist_refuses_production_manifest(
    kb_dir: Path, write_doc: WriteDoc, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md")
    before = DEFAULT_MANIFEST_PATH.exists()

    code = main(
        [
            "--kb-dir",
            str(kb_dir),
            "--manifest",
            str(DEFAULT_MANIFEST_PATH),
            "ingest",
            "--persist-manifest",
        ]
    )

    assert code == 2
    assert "production manifest" in capsys.readouterr().err
    assert DEFAULT_MANIFEST_PATH.exists() == before


def test_cli_rejects_apply_with_persist_manifest(kb_dir: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--kb-dir", str(kb_dir), "ingest", "--apply", "--persist-manifest"])

    assert exc.value.code == 2
