from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ingestion.cli import main
from ingestion.tests.conftest import SAMPLE_BODY

WriteDoc = Callable[..., Path]


def test_validate_succeeds(
    kb_dir: Path, write_doc: WriteDoc, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md")

    assert main(["--kb-dir", str(kb_dir), "validate"]) == 0
    assert "INCLUDED" in capsys.readouterr().out


def test_validate_fails_on_sensitive_content(
    kb_dir: Path, write_doc: WriteDoc, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md", SAMPLE_BODY + "\nReach me at jane.doe@example.com\n")

    assert main(["--kb-dir", str(kb_dir), "validate"]) == 1
    output = capsys.readouterr().out
    assert "EMAIL_ADDRESS" in output
    assert "jane.doe@example.com" not in output


def test_ingest_defaults_to_dry_run(kb_dir: Path, write_doc: WriteDoc, tmp_path: Path) -> None:
    write_doc("resume.md")
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
        ]
    )

    assert code == 0
    assert (output_dir / "report.json").exists()
    assert (output_dir / "chunks.jsonl").exists()
    assert not manifest.exists()


def test_apply_is_refused_without_live_configuration(
    kb_dir: Path, write_doc: WriteDoc, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_doc("resume.md")
    args = ["--kb-dir", str(kb_dir), "--manifest", str(tmp_path / "m.json"), "ingest", "--apply"]

    assert main(args) == 2
    error = capsys.readouterr().err
    assert "ENABLE_LIVE_MODEL_CALLS=true" in error
    assert "OPENAI_API_KEY" in error
    assert "PINECONE_API_KEY" in error


def test_apply_is_refused_when_only_the_live_flag_is_set(
    kb_dir: Path,
    write_doc: WriteDoc,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_doc("resume.md")
    monkeypatch.setenv("ENABLE_LIVE_MODEL_CALLS", "true")
    args = ["--kb-dir", str(kb_dir), "--manifest", str(tmp_path / "m.json"), "ingest", "--apply"]

    assert main(args) == 2
    error = capsys.readouterr().err
    assert "ENABLE_LIVE_MODEL_CALLS" not in error
    assert "OPENAI_EMBEDDING_MODEL" in error


def test_invalid_chunk_configuration(
    kb_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CHUNK_SIZE_TOKENS", "100")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "100")

    assert main(["--kb-dir", str(kb_dir), "validate"]) == 2
    assert "CHUNK_OVERLAP_TOKENS" in capsys.readouterr().err
