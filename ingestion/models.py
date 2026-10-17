from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SOURCE_TYPES = frozenset(
    {
        "RESUME",
        "PROFESSIONAL_PROFILE",
        "PROFESSIONAL_EXPERIENCE",
        "PORTFOLIO_PROJECT",
        "SKILLS_EVIDENCE",
        "EDUCATION",
        "CERTIFICATION",
        "RECRUITER_FAQ",
        "PUBLIC_CONTACT",
    }
)
EXPERIENCE_TYPES = frozenset({"PROFESSIONAL", "PORTFOLIO", "EDUCATION", "GENERAL"})
VISIBILITIES = frozenset({"PUBLIC", "PRIVATE"})

Severity = Literal["ERROR", "WARNING"]
MetadataValue = str | bool | None


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line": self.line,
        }


@dataclass(frozen=True)
class DocumentMetadata:
    source_id: str
    source_type: str
    source_name: str
    section: str
    project_id: str | None
    experience_type: str
    visibility: str
    approved: bool
    source_url: str
    document_version: str
    updated_at: str
    section_experience_types: dict[str, str]


@dataclass(frozen=True)
class Section:
    heading_path: tuple[str, ...]
    heading_levels: tuple[int, ...]
    blocks: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class ParsedDocument:
    path: Path
    raw_metadata: dict[str, object]
    sections: tuple[Section, ...]

    def headings_at_level(self, level: int) -> set[str]:
        return {
            heading
            for section in self.sections
            for heading, heading_level in zip(
                section.heading_path, section.heading_levels, strict=True
            )
            if heading_level == level
        }


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    content: str
    metadata: dict[str, MetadataValue]
    content_hash: str
    token_count: int

    def record_metadata(self) -> dict[str, MetadataValue]:
        return {
            **self.metadata,
            "content": self.content,
            "content_hash": self.content_hash,
            "ingestion_status": "VERIFIED",
        }


@dataclass(frozen=True)
class VectorRecord:
    id: str
    values: list[float]
    metadata: dict[str, MetadataValue]
