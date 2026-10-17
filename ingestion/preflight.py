"""No-network, no-write readiness check before the first live --apply."""

from __future__ import annotations

import socket
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ingestion.config import Settings
from ingestion.pipelines.ingest import build_plan, collect_corpus
from ingestion.pipelines.manifest import load_manifest

_LIVE_FLAGS = ("ENABLE_LIVE_MODEL_CALLS=true", "ENABLE_LIVE_VECTOR_UPSERTS=true")


class NetworkBlockedError(RuntimeError):
    pass


@contextmanager
def block_network() -> Iterator[list[str]]:
    attempts: list[str] = []
    originals = (socket.socket.connect, socket.create_connection, socket.getaddrinfo)

    def refuse(*_: Any, **__: Any) -> Any:
        attempts.append("network")
        raise NetworkBlockedError("network access is blocked during preflight")

    socket.socket.connect = refuse  # type: ignore[method-assign]
    socket.create_connection = refuse
    socket.getaddrinfo = refuse
    try:
        yield attempts
    finally:
        socket.socket.connect, socket.create_connection, socket.getaddrinfo = originals  # type: ignore[method-assign]


def duplicate_env_keys(path: Path) -> list[str]:
    keys = [
        line.strip().removeprefix("export ").split("=", 1)[0].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.strip().startswith("#")
    ]
    return sorted(name for name, count in Counter(keys).items() if count > 1)


def run_preflight(
    kb_dir: Path, manifest_path: Path, settings: Settings, env_file: Path | None
) -> tuple[list[str], list[str]]:
    """Return (report lines, blocking problems). Prints names and booleans only."""
    lines: list[str] = []
    problems: list[str] = []

    documents, chunks = collect_corpus(kb_dir, settings)
    invalid = [d.path for d in documents if d.status == "INVALID"]
    lines.append(f"Corpus: {len(documents)} document(s), {len(chunks)} chunk(s)")
    problems += [f"Invalid document: {path}" for path in invalid]

    plan = build_plan(chunks, load_manifest(manifest_path), settings, for_apply=True)
    lines.append(
        f"Apply plan vs production manifest: {len(plan.new)} new, {len(plan.changed)} changed, "
        f"{len(plan.unchanged)} unchanged, {len(plan.stale)} stale"
    )
    lines += [f"  Note: {note}" for note in plan.notes]

    lines.append(f"ENABLE_LIVE_MODEL_CALLS: {settings.enable_live_calls}")
    lines.append(f"ENABLE_LIVE_VECTOR_UPSERTS: {settings.enable_live_upserts}")
    lines.append(
        "GEMINI_EMBEDDING_DIMENSIONS: "
        + ("set" if settings.embedding_dimensions is not None else "model default")
    )
    missing = settings.missing_live_requirements()
    missing_config = [name for name in missing if name not in _LIVE_FLAGS]
    lines.append(f"Missing apply settings: {', '.join(missing_config) or 'none'}")
    problems += [f"{name} is not set" for name in missing_config]
    pending_flags = [name for name in missing if name in _LIVE_FLAGS]
    lines.append(f"Flags still required for --apply: {', '.join(pending_flags) or 'none'}")

    if env_file is not None:
        duplicates = duplicate_env_keys(env_file)
        if duplicates:
            lines.append(f"Duplicate keys in env file (last value wins): {', '.join(duplicates)}")
    return lines, problems
