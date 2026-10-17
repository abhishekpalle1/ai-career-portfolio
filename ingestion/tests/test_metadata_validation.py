from __future__ import annotations

import datetime as dt

import pytest

from ingestion.validation.metadata import is_safe_source_url, validate_metadata

HEADINGS = {"WORK EXPERIENCE", "SELECTED PROJECTS"}


def valid_raw(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
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
    }
    raw.update(overrides)
    return raw


def codes(raw: dict[str, object]) -> list[str]:
    _, findings = validate_metadata(raw, HEADINGS)
    return [finding.code for finding in findings]


def test_valid_metadata_passes() -> None:
    metadata, findings = validate_metadata(
        valid_raw(section_experience_types={"SELECTED PROJECTS": "PORTFOLIO"}), HEADINGS
    )

    assert findings == []
    assert metadata is not None
    assert metadata.approved is True
    assert metadata.section_experience_types == {"SELECTED PROJECTS": "PORTFOLIO"}


def test_yaml_date_is_normalized() -> None:
    metadata, _ = validate_metadata(valid_raw(updated_at=dt.date(2026, 10, 16)), HEADINGS)

    assert metadata is not None
    assert metadata.updated_at == "2026-10-16"


def test_missing_and_unknown_fields() -> None:
    raw = valid_raw(extra_field="x")
    del raw["visibility"]

    assert sorted(codes(raw)) == ["MISSING_FIELD", "UNKNOWN_FIELD"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_type": "BLOG"},
        {"experience_type": "HOBBY"},
        {"visibility": "INTERNAL"},
        {"approved": "yes"},
        {"source_id": "Resume 2026"},
        {"project_id": "Not A Slug"},
        {"updated_at": "16/10/2026"},
        {"updated_at": "2026-13-01"},
        {"document_version": 2026},
        {"source_name": ""},
    ],
)
def test_invalid_field_values(overrides: dict[str, object]) -> None:
    assert codes(valid_raw(**overrides)) == ["INVALID_FIELD"]


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "http://x.com", "//x.com"],
)
def test_unsafe_source_urls_rejected(url: str) -> None:
    assert not is_safe_source_url(url)
    assert codes(valid_raw(source_url=url)) == ["UNSAFE_SOURCE_URL"]


@pytest.mark.parametrize("url", ["/resume.pdf", "https://github.com/example"])
def test_safe_source_urls_allowed(url: str) -> None:
    assert is_safe_source_url(url)


def test_section_experience_types_must_reference_real_headings() -> None:
    assert codes(valid_raw(section_experience_types={"PROJECTS": "PORTFOLIO"})) == [
        "UNKNOWN_SECTION"
    ]
    assert codes(valid_raw(section_experience_types={"SELECTED PROJECTS": "HOBBY"})) == [
        "INVALID_FIELD"
    ]
