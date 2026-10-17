from __future__ import annotations

from pathlib import Path

from ingestion.chunking.section_chunker import chunk_document, count_tokens, slugify
from ingestion.models import Chunk, Finding
from ingestion.parsers.markdown import parse_markdown_text
from ingestion.tests.conftest import SAMPLE_BODY, document_text
from ingestion.validation.metadata import validate_metadata

FRAUD_ID = "resume-test--work-experience--acme-corp-ml-engineer-2020-present--fraud-platform--001"


def build(
    body: str = SAMPLE_BODY, size: int = 450, overlap: int = 60, **overrides: object
) -> tuple[list[Chunk], list[Finding]]:
    if body != SAMPLE_BODY:
        overrides.setdefault("section_experience_types", {})
    document = parse_markdown_text(document_text(body, **overrides), Path("doc.md"))
    metadata, findings = validate_metadata(document.raw_metadata, document.headings_at_level(2))
    assert metadata is not None, findings
    return chunk_document(document, metadata, chunk_size_tokens=size, chunk_overlap_tokens=overlap)


def by_id(chunks: list[Chunk]) -> dict[str, Chunk]:
    return {chunk.chunk_id: chunk for chunk in chunks}


def test_role_project_and_metrics_stay_in_one_chunk() -> None:
    chunks, findings = build()

    assert findings == []
    assert [c.chunk_id for c in chunks] == [
        "resume-test--summary--001",
        FRAUD_ID,
        "resume-test--selected-projects--demo-assistant--001",
    ]
    fraud = chunks[1]
    assert fraud.content == (
        "Jane Example > WORK EXPERIENCE > Acme Corp, ML Engineer | 2020 - Present > Fraud Platform"
        "\n\n- Built a scoring platform ranking 45K claims."
        "\n- Improved precision 23% -> 40% and F1 0.34 -> 0.52."
    )
    assert fraud.metadata["section"] == "WORK EXPERIENCE"
    assert fraud.token_count == count_tokens(fraud.content)


def test_section_experience_types_drive_attribution() -> None:
    chunks, _ = build()

    assert [c.metadata["experience_type"] for c in chunks] == [
        "GENERAL",
        "PROFESSIONAL",
        "PORTFOLIO",
    ]


def test_ids_and_hashes_are_deterministic() -> None:
    first, _ = build()
    second, _ = build()

    assert [(c.chunk_id, c.content_hash) for c in first] == [
        (c.chunk_id, c.content_hash) for c in second
    ]


def test_hash_changes_with_content_or_metadata() -> None:
    original = by_id(build()[0])
    content_changed = by_id(
        build(
            SAMPLE_BODY.replace("45K", "46K"),
            section_experience_types={
                "WORK EXPERIENCE": "PROFESSIONAL",
                "SELECTED PROJECTS": "PORTFOLIO",
            },
        )[0]
    )
    metadata_changed = by_id(build(section_experience_types={"WORK EXPERIENCE": "PROFESSIONAL"})[0])

    assert content_changed[FRAUD_ID].content_hash != original[FRAUD_ID].content_hash
    demo = "resume-test--selected-projects--demo-assistant--001"
    assert content_changed[demo].content_hash == original[demo].content_hash
    assert metadata_changed[demo].content_hash != original[demo].content_hash


def _bullets(count: int) -> list[str]:
    return [f"- Bullet {i} improved metric {i}0% -> {i}5%." for i in range(1, count + 1)]


def test_long_sections_split_on_whole_bullets_with_overlap() -> None:
    bullets = _bullets(6)
    chunks, findings = build("## Items\n\n" + "\n".join(bullets) + "\n", size=30, overlap=12)

    assert findings == []
    assert [c.chunk_id for c in chunks] == [f"resume-test--items--{i:03d}" for i in range(1, 6)]
    for chunk in chunks:
        assert chunk.content.startswith("Items\n\n")
        assert chunk.token_count <= 30
        assert all(line in bullets for line in chunk.content.split("\n\n", 1)[1].split("\n"))
    for bullet in bullets:
        assert any(bullet in chunk.content for chunk in chunks)
    # Overlap: each chunk repeats the last bullet of the previous chunk.
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous.content.split("\n")[-1] in current.content


def test_zero_overlap_produces_disjoint_chunks() -> None:
    chunks, _ = build("## Items\n\n" + "\n".join(_bullets(6)) + "\n", size=30, overlap=0)

    assert len(chunks) == 3


def test_oversized_block_is_kept_intact_with_warning() -> None:
    long_bullet = "- " + " ".join(f"word{i}" for i in range(40))
    chunks, findings = build(f"## Items\n\n{long_bullet}\n", size=20, overlap=0)

    assert [f.code for f in findings] == ["OVERSIZED_BLOCK"]
    assert findings[0].severity == "WARNING"
    assert long_bullet in chunks[0].content


def test_duplicate_heading_paths_are_errors() -> None:
    chunks, findings = build("## Same\n\nOne\n\n## Same\n\nTwo\n")

    assert [c.chunk_id for c in chunks] == ["resume-test--same--001"]
    assert [f.code for f in findings] == ["DUPLICATE_CHUNK_ID"]


def test_preamble_without_heading_uses_source_name() -> None:
    chunks, _ = build("Intro paragraph.\n")

    assert chunks[0].chunk_id == "resume-test--preamble--001"
    assert chunks[0].content == "Resume\n\nIntro paragraph."


def test_slugify() -> None:
    assert slugify("Workers' Compensation – Claims & More") == "workers-compensation-claims-more"
