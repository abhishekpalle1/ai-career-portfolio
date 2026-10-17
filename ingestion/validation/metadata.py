from __future__ import annotations

import datetime as dt
import re
from collections.abc import Collection, Mapping
from urllib.parse import urlsplit

from ingestion.models import (
    EXPERIENCE_TYPES,
    SOURCE_TYPES,
    VISIBILITIES,
    DocumentMetadata,
    Finding,
)

REQUIRED_FIELDS = (
    "source_id",
    "source_type",
    "source_name",
    "section",
    "project_id",
    "experience_type",
    "visibility",
    "approved",
    "source_url",
    "document_version",
    "updated_at",
)
OPTIONAL_FIELDS = ("section_experience_types",)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_safe_source_url(url: str) -> bool:
    """Allow site-relative paths and absolute https URLs only."""
    if url.startswith("/") and not url.startswith("//"):
        return True
    parts = urlsplit(url)
    return parts.scheme == "https" and bool(parts.netloc)


def validate_metadata(
    raw: Mapping[str, object], level_two_headings: Collection[str]
) -> tuple[DocumentMetadata | None, list[Finding]]:
    errors: list[Finding] = []

    def error(code: str, message: str) -> None:
        errors.append(Finding("ERROR", code, message))

    for name in REQUIRED_FIELDS:
        if name not in raw:
            error("MISSING_FIELD", f"Missing required field '{name}'")
    for name in raw:
        if name not in REQUIRED_FIELDS and name not in OPTIONAL_FIELDS:
            error("UNKNOWN_FIELD", f"Unknown field '{name}'")

    def text_field(name: str) -> str:
        value = raw.get(name)
        if name in raw and (not isinstance(value, str) or not value.strip()):
            error("INVALID_FIELD", f"'{name}' must be a non-empty string")
        return value.strip() if isinstance(value, str) else ""

    source_id = text_field("source_id")
    if source_id and not _SLUG_RE.match(source_id):
        error("INVALID_FIELD", "'source_id' must be a lowercase hyphenated slug")

    source_type = text_field("source_type")
    if source_type and source_type not in SOURCE_TYPES:
        error("INVALID_FIELD", f"'source_type' must be one of {sorted(SOURCE_TYPES)}")

    experience_type = text_field("experience_type")
    if experience_type and experience_type not in EXPERIENCE_TYPES:
        error("INVALID_FIELD", f"'experience_type' must be one of {sorted(EXPERIENCE_TYPES)}")

    visibility = text_field("visibility")
    if visibility and visibility not in VISIBILITIES:
        error("INVALID_FIELD", f"'visibility' must be one of {sorted(VISIBILITIES)}")

    source_name = text_field("source_name")
    section = text_field("section")
    document_version = text_field("document_version")

    source_url = text_field("source_url")
    if source_url and not is_safe_source_url(source_url):
        error("UNSAFE_SOURCE_URL", "'source_url' must be a site-relative path or an https URL")

    approved = raw.get("approved")
    if "approved" in raw and not isinstance(approved, bool):
        error("INVALID_FIELD", "'approved' must be true or false")

    project_id = raw.get("project_id")
    if project_id is not None and (
        not isinstance(project_id, str) or not _SLUG_RE.match(project_id)
    ):
        error("INVALID_FIELD", "'project_id' must be null or a lowercase hyphenated slug")

    updated_at = _normalize_date(raw.get("updated_at"))
    if "updated_at" in raw and updated_at is None:
        error("INVALID_FIELD", "'updated_at' must be a YYYY-MM-DD date")

    section_types: dict[str, str] = {}
    raw_section_types = raw.get("section_experience_types", {})
    if not isinstance(raw_section_types, dict):
        error("INVALID_FIELD", "'section_experience_types' must be a mapping")
    else:
        for heading, value in raw_section_types.items():
            if heading not in level_two_headings:
                error(
                    "UNKNOWN_SECTION",
                    f"'section_experience_types' references missing '## {heading}' heading",
                )
            elif value not in EXPERIENCE_TYPES:
                error("INVALID_FIELD", f"Experience type for '{heading}' is not allowed")
            else:
                section_types[str(heading)] = str(value)

    if errors:
        return None, errors
    return (
        DocumentMetadata(
            source_id=source_id,
            source_type=source_type,
            source_name=source_name,
            section=section,
            project_id=project_id if isinstance(project_id, str) else None,
            experience_type=experience_type,
            visibility=visibility,
            approved=bool(approved),
            source_url=source_url,
            document_version=document_version,
            updated_at=updated_at or "",
            section_experience_types=section_types,
        ),
        [],
    )


def _normalize_date(value: object) -> str | None:
    if isinstance(value, dt.datetime):
        return None
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, str) and _DATE_RE.match(value):
        try:
            return dt.date.fromisoformat(value).isoformat()
        except ValueError:
            return None
    return None
