from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from ingestion.models import Chunk, DocumentMetadata, Finding, MetadataValue, ParsedDocument
from ingestion.parsers.markdown import is_list_item

MAX_CHUNK_ID_LENGTH = 512  # Pinecone record-ID limit.

# Approximation (words + punctuation), so chunking stays offline and dependency-free.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def count_tokens(text: str) -> int:
    return len(_TOKEN_RE.findall(text))


def slugify(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower().replace("'", "")).strip("-")


def compute_content_hash(content: str, metadata: dict[str, MetadataValue]) -> str:
    """Covers text and metadata, so metadata-only edits are re-upserted too."""
    payload = json.dumps({"content": content, "metadata": metadata}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunk_document(
    document: ParsedDocument,
    metadata: DocumentMetadata,
    *,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> tuple[list[Chunk], list[Finding]]:
    chunks: list[Chunk] = []
    findings: list[Finding] = []
    seen_ids: set[str] = set()

    for section in document.sections:
        path = section.heading_path
        breadcrumb = " > ".join(path) or metadata.source_name
        top_section = next(
            (h for h, level in zip(path, section.heading_levels, strict=True) if level == 2),
            metadata.section,
        )
        experience_type = metadata.section_experience_types.get(
            top_section, metadata.experience_type
        )

        budget = chunk_size_tokens - count_tokens(breadcrumb)
        groups, oversized = _pack_blocks(list(section.blocks), budget, chunk_overlap_tokens)
        if oversized:
            findings.append(
                Finding(
                    "WARNING",
                    "OVERSIZED_BLOCK",
                    f"{oversized} block(s) exceed the chunk budget and were kept intact",
                    section.line,
                )
            )

        segments = [slugify(h) for h, level in zip(path, section.heading_levels, strict=True)]
        if len(segments) > 1 and section.heading_levels[0] == 1:
            segments = segments[1:]
        path_slug = "--".join(s for s in segments if s) or "preamble"

        for index, group in enumerate(groups, start=1):
            chunk_id = f"{metadata.source_id}--{path_slug}--{index:03d}"
            if chunk_id in seen_ids:
                findings.append(
                    Finding("ERROR", "DUPLICATE_CHUNK_ID", "Duplicate heading path", section.line)
                )
                continue
            if len(chunk_id) > MAX_CHUNK_ID_LENGTH:
                findings.append(
                    Finding("ERROR", "CHUNK_ID_TOO_LONG", "Heading path too long", section.line)
                )
                continue
            seen_ids.add(chunk_id)

            separator = "\n" if all(is_list_item(block) for block in group) else "\n\n"
            content = f"{breadcrumb}\n\n{separator.join(group)}"
            chunk_metadata: dict[str, MetadataValue] = {
                "chunk_id": chunk_id,
                "source_id": metadata.source_id,
                "source_type": metadata.source_type,
                "source_name": metadata.source_name,
                "section": top_section,
                "heading_path": breadcrumb,
                "project_id": metadata.project_id,
                "experience_type": experience_type,
                "visibility": metadata.visibility,
                "approved": metadata.approved,
                "source_url": metadata.source_url,
                "document_version": metadata.document_version,
                "updated_at": metadata.updated_at,
            }
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    content=content,
                    metadata=chunk_metadata,
                    content_hash=compute_content_hash(content, chunk_metadata),
                    token_count=count_tokens(content),
                )
            )
    return chunks, findings


def _pack_blocks(blocks: list[str], budget: int, overlap: int) -> tuple[list[list[str]], int]:
    """Greedily pack whole blocks; a bullet is never split from its own metrics."""
    groups: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    oversized = 0

    for block in blocks:
        tokens = count_tokens(block)
        if tokens > budget:
            oversized += 1
        if current and current_tokens + tokens > budget:
            groups.append(current)
            carry = _overlap_tail(current, overlap)
            carry_tokens = sum(count_tokens(b) for b in carry)
            if carry_tokens + tokens > budget:
                carry, carry_tokens = [], 0
            current, current_tokens = carry, carry_tokens
        current.append(block)
        current_tokens += tokens
    if current:
        groups.append(current)
    return groups, oversized


def _overlap_tail(blocks: list[str], overlap: int) -> list[str]:
    tail: list[str] = []
    total = 0
    for block in reversed(blocks[1:]):
        tokens = count_tokens(block)
        if total + tokens > overlap:
            break
        tail.insert(0, block)
        total += tokens
    return tail
