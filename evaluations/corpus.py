"""Ground truth: the approved corpus as produced by the ingestion pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from evaluations import REPO_ROOT

DEFAULT_KB_DIR = REPO_ROOT / "knowledge-base"
DEFAULT_MANIFEST = REPO_ROOT / "ingestion" / "state" / "manifest.json"


@dataclass(frozen=True)
class CorpusChunk:
    chunk_id: str
    section: str
    experience_type: str
    heading_path: str
    content: str
    content_hash: str


def load_corpus(kb_dir: Path = DEFAULT_KB_DIR) -> dict[str, CorpusChunk]:
    from ingestion.config import Settings as IngestionSettings
    from ingestion.pipelines.ingest import collect_corpus

    _, chunks = collect_corpus(kb_dir, IngestionSettings())
    return {
        chunk.chunk_id: CorpusChunk(
            chunk_id=chunk.chunk_id,
            section=str(chunk.metadata["section"]),
            experience_type=str(chunk.metadata["experience_type"]),
            heading_path=str(chunk.metadata["heading_path"]),
            content=chunk.content,
            content_hash=chunk.content_hash,
        )
        for chunk in chunks
    }


def corpus_matches_manifest(corpus: dict[str, CorpusChunk], manifest_path: Path) -> bool:
    """True when the local corpus is exactly what was last upserted to Pinecone."""
    if not manifest_path.exists():
        return False
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))["chunks"]
    return set(entries) == set(corpus) and all(
        entries[cid]["content_hash"] == chunk.content_hash for cid, chunk in corpus.items()
    )


def employer_names(corpus: dict[str, CorpusChunk]) -> set[str]:
    names: set[str] = set()
    for chunk in corpus.values():
        parts = chunk.heading_path.split(" > ")
        if chunk.experience_type == "PROFESSIONAL" and len(parts) >= 3:
            names.add(parts[2].split(",")[0].strip())
    return names


def portfolio_titles(corpus: dict[str, CorpusChunk]) -> set[str]:
    return {
        chunk.heading_path.split(" > ")[-1].strip()
        for chunk in corpus.values()
        if chunk.experience_type == "PORTFOLIO"
    }
