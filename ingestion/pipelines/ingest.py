from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from ingestion.adapters.base import Embedder, VectorStore
from ingestion.chunking.section_chunker import chunk_document
from ingestion.config import Settings
from ingestion.models import Chunk, Finding, VectorRecord
from ingestion.parsers.markdown import ParseError, parse_markdown_text
from ingestion.pipelines.manifest import Manifest, ManifestEntry, load_manifest, save_manifest
from ingestion.validation.metadata import validate_metadata
from ingestion.validation.sensitive import scan_sensitive_content

INCLUDED = "INCLUDED"
SKIPPED_UNAPPROVED = "SKIPPED_UNAPPROVED"
SKIPPED_NOT_PUBLIC = "SKIPPED_NOT_PUBLIC"
INVALID = "INVALID"


class IngestionError(RuntimeError):
    pass


@dataclass
class DocumentResult:
    path: str
    source_id: str | None = None
    status: str = INVALID
    findings: list[Finding] = field(default_factory=list)
    chunk_count: int = 0


@dataclass
class Plan:
    new: list[str]
    changed: list[str]
    unchanged: list[str]
    stale: list[str]
    notes: list[str]


@dataclass
class RunResult:
    mode: str
    documents: list[DocumentResult]
    chunks: list[Chunk]
    plan: Plan | None = None
    embedded: int = 0
    upserted: int = 0
    deleted: int = 0

    @property
    def ok(self) -> bool:
        return all(document.status != INVALID for document in self.documents)


def _has_errors(findings: list[Finding]) -> bool:
    return any(finding.severity == "ERROR" for finding in findings)


def collect_corpus(kb_dir: Path, settings: Settings) -> tuple[list[DocumentResult], list[Chunk]]:
    results: list[DocumentResult] = []
    chunks: list[Chunk] = []
    seen_source_ids: set[str] = set()

    for path in sorted(kb_dir.rglob("*.md")):
        result = DocumentResult(path=path.relative_to(kb_dir).as_posix())
        results.append(result)
        text = path.read_text(encoding="utf-8")
        try:
            document = parse_markdown_text(text, path)
        except ParseError as exc:
            result.findings.append(Finding("ERROR", "PARSE_ERROR", str(exc)))
            continue

        metadata, metadata_findings = validate_metadata(
            document.raw_metadata, document.headings_at_level(2)
        )
        result.findings.extend(metadata_findings)
        allow_email = document.raw_metadata.get("source_type") == "PUBLIC_CONTACT"
        result.findings.extend(scan_sensitive_content(text, allow_email=allow_email))
        if metadata is None or _has_errors(result.findings):
            continue

        result.source_id = metadata.source_id
        if metadata.source_id in seen_source_ids:
            result.findings.append(
                Finding("ERROR", "DUPLICATE_SOURCE_ID", "source_id is used by another document")
            )
            continue
        seen_source_ids.add(metadata.source_id)

        if not metadata.approved:
            result.status = SKIPPED_UNAPPROVED
            continue
        if metadata.visibility != "PUBLIC":
            result.status = SKIPPED_NOT_PUBLIC
            continue

        document_chunks, chunk_findings = chunk_document(
            document,
            metadata,
            chunk_size_tokens=settings.chunk_size_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
        )
        result.findings.extend(chunk_findings)
        if _has_errors(chunk_findings):
            continue
        result.status = INCLUDED
        result.chunk_count = len(document_chunks)
        chunks.extend(document_chunks)

    return results, chunks


def build_plan(
    chunks: list[Chunk], manifest: Manifest | None, settings: Settings, *, for_apply: bool = False
) -> Plan:
    notes: list[str] = []
    previous: dict[str, ManifestEntry] = {}
    full_reindex = False

    if manifest is None:
        notes.append("No manifest found; every chunk is new.")
    elif for_apply and manifest.offline:
        notes.append(
            "Manifest was written offline, not by Pinecone upserts; treating target as empty."
        )
    elif (manifest.pinecone_index, manifest.pinecone_namespace) != (
        settings.pinecone_index,
        settings.pinecone_namespace,
    ):
        notes.append("Manifest targets a different index or namespace; treating target as empty.")
    else:
        previous = manifest.chunks
        if settings.embedding_model is None or not manifest.embedding_model:
            notes.append("Embedding model unknown; model-change detection skipped.")
        elif manifest.embedding_model != settings.embedding_model:
            full_reindex = True
            notes.append("Embedding model changed; every chunk will be re-embedded.")

    new: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    for chunk in chunks:
        entry = previous.get(chunk.chunk_id)
        if entry is None:
            new.append(chunk.chunk_id)
        elif full_reindex or entry.content_hash != chunk.content_hash:
            changed.append(chunk.chunk_id)
        else:
            unchanged.append(chunk.chunk_id)

    current_ids = {chunk.chunk_id for chunk in chunks}
    stale = sorted(chunk_id for chunk_id in previous if chunk_id not in current_ids)
    return Plan(new=new, changed=changed, unchanged=unchanged, stale=stale, notes=notes)


def validate_corpus(kb_dir: Path, settings: Settings) -> RunResult:
    documents, chunks = collect_corpus(kb_dir, settings)
    return RunResult(mode="validate", documents=documents, chunks=chunks)


def run_ingestion(
    kb_dir: Path,
    settings: Settings,
    *,
    manifest_path: Path,
    apply: bool = False,
    persist_manifest: bool = False,
    delete_stale: bool = False,
    embedder: Embedder | None = None,
    store: VectorStore | None = None,
) -> RunResult:
    if apply and persist_manifest:
        raise IngestionError("persist_manifest is offline-only and cannot be combined with apply")
    documents, chunks = collect_corpus(kb_dir, settings)
    manifest = load_manifest(manifest_path)
    plan = build_plan(chunks, manifest, settings, for_apply=apply)
    mode = "apply" if apply else "offline-persist" if persist_manifest else "dry-run"
    result = RunResult(mode=mode, documents=documents, chunks=chunks, plan=plan)
    if not apply and not persist_manifest:
        return result
    if not result.ok:
        raise IngestionError(f"Refusing to {mode}: the corpus contains invalid documents")
    if persist_manifest:
        _write_manifest(
            manifest_path,
            chunks,
            plan,
            manifest,
            settings,
            delete_stale=delete_stale,
            embedding_model=settings.embedding_model or "",
            offline=True,
        )
        return result
    if embedder is None or store is None:
        raise IngestionError("Apply mode requires an embedder and a vector store")

    pending_ids = set(plan.new) | set(plan.changed)
    pending = [chunk for chunk in chunks if chunk.chunk_id in pending_ids]
    if pending:
        vectors = embedder.embed([chunk.content for chunk in pending])
        store.upsert(
            [
                VectorRecord(id=chunk.chunk_id, values=vector, metadata=chunk.record_metadata())
                for chunk, vector in zip(pending, vectors, strict=True)
            ]
        )
    result.embedded = result.upserted = len(pending)

    if delete_stale and plan.stale:
        store.delete(plan.stale)
        result.deleted = len(plan.stale)

    _write_manifest(
        manifest_path,
        chunks,
        plan,
        manifest,
        settings,
        delete_stale=delete_stale,
        embedding_model=embedder.model,
        offline=False,
    )
    return result


def _write_manifest(
    path: Path,
    chunks: list[Chunk],
    plan: Plan,
    previous: Manifest | None,
    settings: Settings,
    *,
    delete_stale: bool,
    embedding_model: str,
    offline: bool,
) -> None:
    entries = {
        chunk.chunk_id: ManifestEntry(str(chunk.metadata["source_id"]), chunk.content_hash)
        for chunk in chunks
    }
    if previous is not None and not delete_stale:
        # Stale vectors still exist in Pinecone, so keep tracking them.
        entries.update({chunk_id: previous.chunks[chunk_id] for chunk_id in plan.stale})
    save_manifest(
        path,
        Manifest(
            embedding_model=embedding_model,
            pinecone_index=settings.pinecone_index,
            pinecone_namespace=settings.pinecone_namespace,
            updated_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            chunks=entries,
            offline=offline,
        ),
    )
