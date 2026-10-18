"""Every evaluation test is hermetic: no live flags, no keys, no non-loopback sockets."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from evaluations.corpus import CorpusChunk, load_corpus
from evaluations.dataset import EvalCase

LIVE_ENV_VARS = (
    "ENABLE_LIVE_MODEL_CALLS",
    "ENABLE_LIVE_RAG",
    "ENABLE_LIVE_VECTOR_UPSERTS",
    "GEMINI_API_KEY",
    "PINECONE_API_KEY",
    "PINECONE_INDEX",
    "PINECONE_NAMESPACE",
)
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def blocked_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Clears live configuration and records (and refuses) any external connection attempt."""
    for name in LIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    attempts: list[str] = []
    real_connect = socket.socket.connect

    def guarded(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in _LOOPBACK:
            attempts.append(host)
            raise RuntimeError(f"external network call blocked in tests: {host}")
        real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    return attempts


@pytest.fixture(scope="session")
def corpus() -> dict[str, CorpusChunk]:
    return load_corpus()


EDU = "resume-abhishek-palle-current--education--001"


def make_case(**overrides: Any) -> EvalCase:
    base: dict[str, Any] = {
        "case_id": "t-1",
        "category": "education",
        "question": "Where did he study?",
        "expected_intent": "EDUCATION",
        "expected_behavior": "ANSWER",
        "relevant_chunk_ids": [EDU],
        "evidence_groups": [],
        "acceptable_chunk_ids": [],
        "required_facts": ["Texas A&M"],
        "forbidden_claims": [],
        "expected_experience_type": "EDUCATION",
    }
    return EvalCase.model_validate(base | overrides)
