"""Regression checks against the committed, approved knowledge base."""

from __future__ import annotations

import pytest

from ingestion.config import DEFAULT_KB_DIR, Settings
from ingestion.models import Chunk
from ingestion.pipelines.ingest import INCLUDED, RunResult, validate_corpus
from ingestion.pipelines.report import format_summary
from ingestion.validation.sensitive import scan_sensitive_content


@pytest.fixture(scope="module")
def corpus() -> RunResult:
    return validate_corpus(DEFAULT_KB_DIR, Settings())


@pytest.fixture(scope="module")
def resume_chunks(corpus: RunResult) -> list[Chunk]:
    return [c for c in corpus.chunks if c.metadata["source_id"] == "resume-abhishek-palle-current"]


def test_knowledge_base_validates(corpus: RunResult) -> None:
    assert corpus.ok, format_summary(corpus)
    resume = next(d for d in corpus.documents if d.path == "resume/resume.md")
    assert resume.status == INCLUDED
    assert [f for f in resume.findings if f.severity == "ERROR"] == []


def test_resume_sections_have_expected_attribution(resume_chunks: list[Chunk]) -> None:
    assert {c.metadata["section"]: c.metadata["experience_type"] for c in resume_chunks} == {
        "SUMMARY": "GENERAL",
        "TECHNICAL SKILLS": "GENERAL",
        "WORK EXPERIENCE": "PROFESSIONAL",
        "SELECTED PROJECTS": "PORTFOLIO",
        "EDUCATION": "EDUCATION",
    }


def test_every_work_chunk_carries_its_role_heading(resume_chunks: list[Chunk]) -> None:
    work = [c for c in resume_chunks if c.metadata["section"] == "WORK EXPERIENCE"]

    assert work
    for chunk in work:
        heading_path = str(chunk.metadata["heading_path"])
        role = heading_path.split(" > ")[2]
        assert " | " in role
        assert chunk.content.startswith(heading_path)


def test_resume_chunks_contain_no_private_or_placeholder_values(
    resume_chunks: list[Chunk],
) -> None:
    for chunk in resume_chunks:
        assert scan_sensitive_content(chunk.content) == []
        assert chunk.metadata["approved"] is True
        assert chunk.metadata["visibility"] == "PUBLIC"
