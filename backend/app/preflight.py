"""No-network, no-write preflight for the live RAG path. Run from backend/: python -m app.preflight

Prints setting names and booleans only, never values.
"""

from __future__ import annotations

import re
import socket
import sys
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.rag_assistant import AssistantUnavailableError, RagAssistant

ENV_FILE = Path(".env")
# gemini-embedding-2 output range per Google's embeddings documentation.
GEMINI_MIN_DIMENSIONS = 128
GEMINI_MAX_DIMENSIONS = 3072
_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


class NetworkBlockedError(RuntimeError):
    pass


@contextmanager
def block_network() -> Iterator[list[str]]:
    """Fail any socket connection or DNS lookup attempted inside the block."""
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
    if not path.exists():
        return []
    keys = [
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := _KEY_RE.match(line))
    ]
    return sorted(name for name, count in Counter(keys).items() if count > 1)


def run_preflight(settings: Settings, env_file: Path | None) -> tuple[list[str], list[str]]:
    """Return (report lines, blocking problems)."""
    lines: list[str] = []
    problems: list[str] = []

    lines.append(f"ENABLE_LIVE_MODEL_CALLS: {settings.enable_live_model_calls}")
    lines.append(f"ENABLE_LIVE_RAG: {settings.enable_live_rag}")
    lines.append(f"Live RAG active: {settings.live_rag_enabled}")

    missing = settings.missing_live_rag_settings()
    lines.append(f"Missing live settings: {', '.join(missing) or 'none'}")
    problems += [f"{name} is not set" for name in missing]

    if env_file is not None:
        duplicates = duplicate_env_keys(env_file)
        if duplicates:
            lines.append(f"Duplicate keys in env file (last value wins): {', '.join(duplicates)}")

    dims = settings.gemini_embedding_dimensions
    if dims is not None and not GEMINI_MIN_DIMENSIONS <= dims <= GEMINI_MAX_DIMENSIONS:
        problems.append("GEMINI_EMBEDDING_DIMENSIONS must be between 128 and 3072")
    if not 0 < settings.final_context_chunks <= settings.retrieval_top_k:
        problems.append("FINAL_CONTEXT_CHUNKS must be between 1 and RETRIEVAL_TOP_K")
    if settings.gemini_max_output_tokens <= 0:
        problems.append("GEMINI_MAX_OUTPUT_TOKENS must be positive")
    if settings.external_timeout_seconds <= 0:
        problems.append("EXTERNAL_TIMEOUT_SECONDS must be positive")
    lines.append(f"GEMINI_EMBEDDING_MODEL: {settings.gemini_embedding_model or 'unset'}")
    lines.append(f"GEMINI_EMBEDDING_DIMENSIONS: {dims if dims is not None else 'unset'}")
    lines.append(f"GEMINI_GENERATION_MODEL: {settings.gemini_generation_model or 'unset'}")
    lines.append(
        "MIN_RETRIEVAL_SCORE: "
        + ("set" if settings.min_retrieval_score is not None else "unset (no threshold yet)")
    )

    if not missing:
        try:
            RagAssistant.from_settings(settings)
            lines.append("Live clients constructed offline: yes")
        except (AssistantUnavailableError, ImportError, ValueError) as exc:
            problems.append(f"Live client construction failed: {type(exc).__name__}")
    return lines, problems


def main() -> int:
    with block_network() as attempts:
        settings = Settings()
        lines, problems = run_preflight(settings, ENV_FILE)
    print("Backend live-RAG preflight (no network, no writes)")
    for line in lines:
        print(f"  {line}")
    print(f"  Network attempts blocked: {len(attempts)}")
    for problem in problems:
        print(f"  PROBLEM: {problem}")
    print(
        "Result: "
        + ("READY (live flags still control activation)" if not problems else "NOT READY")
    )
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
