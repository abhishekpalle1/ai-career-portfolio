from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from ingestion.config import Settings
from ingestion.pipelines.ingest import (
    INCLUDED,
    INVALID,
    SKIPPED_NOT_PUBLIC,
    SKIPPED_UNAPPROVED,
    IngestionError,
    run_ingestion,
)
from ingestion.pipelines.manifest import load_manifest
from ingestion.pipelines.report import write_reports
from ingestion.tests.conftest import SAMPLE_BODY, FakeEmbedder, FakeStore

FRAUD_ID = "resume-test--work-experience--acme-corp-ml-engineer-2020-present--fraud-platform--001"
DEMO_ID = "resume-test--selected-projects--demo-assistant--001"
WriteDoc = Callable[..., Path]


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "manifest.json"


def test_dry_run_plans_new_chunks_and_skips_unapproved_and_private(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume/resume.md")
    write_doc(
        "drafts/draft.md",
        "## Draft\n\nUnreviewed draft text\n",
        source_id="draft",
        approved=False,
        section_experience_types={},
    )
    write_doc(
        "private/notes.md",
        "## Notes\n\nPrivate notes text\n",
        source_id="notes",
        visibility="PRIVATE",
        section_experience_types={},
    )

    result = run_ingestion(kb_dir, settings, manifest_path=manifest_path)

    assert result.ok
    assert {d.path: d.status for d in result.documents} == {
        "drafts/draft.md": SKIPPED_UNAPPROVED,
        "private/notes.md": SKIPPED_NOT_PUBLIC,
        "resume/resume.md": INCLUDED,
    }
    assert result.plan is not None
    assert len(result.plan.new) == 3
    assert result.plan.changed == result.plan.unchanged == result.plan.stale == []
    assert not any("draft" in c.content or "Private" in c.content for c in result.chunks)
    assert not manifest_path.exists()


def test_invalid_documents_fail_the_run_and_block_apply(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md", SAMPLE_BODY + "\nCall 555-010-0199\n")
    store = FakeStore()

    result = run_ingestion(kb_dir, settings, manifest_path=manifest_path)
    assert not result.ok
    assert result.documents[0].status == INVALID
    assert [f.code for f in result.documents[0].findings] == ["PHONE_NUMBER"]

    with pytest.raises(IngestionError):
        run_ingestion(
            kb_dir,
            settings,
            manifest_path=manifest_path,
            apply=True,
            embedder=FakeEmbedder(),
            store=store,
        )
    assert store.records == {}
    assert not manifest_path.exists()


def test_duplicate_source_ids_are_rejected(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("a.md")
    write_doc("b.md")

    result = run_ingestion(kb_dir, settings, manifest_path=manifest_path)

    assert not result.ok
    assert result.documents[1].findings[0].code == "DUPLICATE_SOURCE_ID"


def test_apply_upserts_records_and_rerun_is_idempotent(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md")
    store = FakeStore()

    first = run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    assert first.upserted == 3
    record = store.records[FRAUD_ID]
    assert record.metadata["approved"] is True
    assert record.metadata["visibility"] == "PUBLIC"
    assert record.metadata["ingestion_status"] == "VERIFIED"
    assert record.metadata["experience_type"] == "PROFESSIONAL"
    assert record.metadata["content"] == first.chunks[1].content
    assert store.records[DEMO_ID].metadata["experience_type"] == "PORTFOLIO"

    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert set(manifest.chunks) == set(store.records)
    assert "45K claims" not in manifest_path.read_text(encoding="utf-8")

    rerun_embedder = FakeEmbedder()
    second = run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=rerun_embedder,
        store=store,
    )

    assert second.plan is not None
    assert len(second.plan.unchanged) == 3
    assert second.embedded == second.upserted == 0
    assert rerun_embedder.calls == []
    assert store.upsert_calls == 1


def test_only_changed_chunks_are_reembedded(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md")
    store = FakeStore()
    run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    write_doc("resume.md", SAMPLE_BODY.replace("45K", "46K"))
    embedder = FakeEmbedder()
    result = run_ingestion(
        kb_dir, settings, manifest_path=manifest_path, apply=True, embedder=embedder, store=store
    )

    assert result.plan is not None
    assert result.plan.changed == [FRAUD_ID]
    assert len(embedder.calls) == 1
    assert len(embedder.calls[0]) == 1
    assert "46K" in str(store.records[FRAUD_ID].metadata["content"])


def test_stale_chunks_are_deleted_only_when_requested(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md")
    store = FakeStore()
    run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    write_doc(
        "resume.md",
        SAMPLE_BODY.split("## SELECTED PROJECTS")[0],
        section_experience_types={"WORK EXPERIENCE": "PROFESSIONAL"},
    )
    kept = run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    assert kept.plan is not None
    assert kept.plan.stale == [DEMO_ID]
    assert kept.deleted == 0
    assert DEMO_ID in store.records
    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert DEMO_ID in manifest.chunks

    deleted = run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        delete_stale=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    assert deleted.deleted == 1
    assert store.deleted == [DEMO_ID]
    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert DEMO_ID not in manifest.chunks
    final = run_ingestion(kb_dir, settings, manifest_path=manifest_path)
    assert final.plan is not None
    assert final.plan.stale == []


def test_embedding_model_change_forces_full_reindex(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md")
    store = FakeStore()
    run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=store,
    )

    new_settings = Settings(embedding_model="other-model")
    result = run_ingestion(
        kb_dir,
        new_settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder("other-model"),
        store=store,
    )

    assert result.plan is not None
    assert len(result.plan.changed) == 3
    assert any("Embedding model changed" in note for note in result.plan.notes)
    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert manifest.embedding_model == "other-model"


def test_different_namespace_starts_from_empty_target(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md")
    run_ingestion(
        kb_dir,
        settings,
        manifest_path=manifest_path,
        apply=True,
        embedder=FakeEmbedder(),
        store=FakeStore(),
    )

    staging = Settings(embedding_model="test-embedding-model", pinecone_namespace="staging")
    result = run_ingestion(kb_dir, staging, manifest_path=manifest_path)

    assert result.plan is not None
    assert len(result.plan.new) == 3
    assert result.plan.stale == []


def test_apply_requires_adapters(
    kb_dir: Path, write_doc: WriteDoc, settings: Settings, manifest_path: Path
) -> None:
    write_doc("resume.md")

    with pytest.raises(IngestionError):
        run_ingestion(kb_dir, settings, manifest_path=manifest_path, apply=True)


def test_reports_are_written_without_secrets(
    kb_dir: Path, write_doc: WriteDoc, manifest_path: Path, tmp_path: Path
) -> None:
    write_doc("resume.md")
    fake_key = "not-a-real-gemini-key-000000000000"
    settings = Settings(
        embedding_model="test-embedding-model", gemini_api_key=fake_key, pinecone_api_key=fake_key
    )
    result = run_ingestion(kb_dir, settings, manifest_path=manifest_path)

    paths = write_reports(result, settings, tmp_path / "out")

    assert [p.name for p in paths] == ["report.json", "report.md", "chunks.jsonl"]
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run"
    assert report["totals"]["chunks"] == 3
    assert len(paths[2].read_text(encoding="utf-8").splitlines()) == 3
    for path in paths:
        assert fake_key not in path.read_text(encoding="utf-8")
    assert fake_key not in repr(settings)
