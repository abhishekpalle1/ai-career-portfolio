from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_VERSION = 1


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class ManifestEntry:
    source_id: str
    content_hash: str


@dataclass(frozen=True)
class Manifest:
    """What was last upserted to a specific Pinecone index/namespace. Contains no chunk text."""

    embedding_model: str
    pinecone_index: str
    pinecone_namespace: str
    updated_at: str
    chunks: dict[str, ManifestEntry]
    # Written by --persist-manifest without touching Pinecone; --apply ignores it.
    offline: bool = False


def load_manifest(path: Path) -> Manifest | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["manifest_version"] != MANIFEST_VERSION:
            raise ManifestError(f"Unsupported manifest version in {path}")
        return Manifest(
            embedding_model=str(data["embedding_model"]),
            pinecone_index=str(data["pinecone_index"]),
            pinecone_namespace=str(data["pinecone_namespace"]),
            updated_at=str(data["updated_at"]),
            chunks={
                chunk_id: ManifestEntry(str(entry["source_id"]), str(entry["content_hash"]))
                for chunk_id, entry in data["chunks"].items()
            },
            offline=data.get("offline", False) is True,
        )
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Malformed manifest at {path}") from exc


def save_manifest(path: Path, manifest: Manifest) -> None:
    data = {
        "manifest_version": MANIFEST_VERSION,
        "embedding_model": manifest.embedding_model,
        "pinecone_index": manifest.pinecone_index,
        "pinecone_namespace": manifest.pinecone_namespace,
        "updated_at": manifest.updated_at,
        "offline": manifest.offline,
        "chunks": {
            chunk_id: {"source_id": entry.source_id, "content_hash": entry.content_hash}
            for chunk_id, entry in sorted(manifest.chunks.items())
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
