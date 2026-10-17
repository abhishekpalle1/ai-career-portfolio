import socket
from pathlib import Path

import pytest

from app.preflight import NetworkBlockedError, block_network, duplicate_env_keys, run_preflight
from tests.rag_fakes import DUMMY_KEY, live_settings


def test_block_network_refuses_connections_and_restores_socket() -> None:
    original = socket.create_connection
    with block_network() as attempts:
        with pytest.raises(NetworkBlockedError):
            socket.create_connection(("example.com", 443))
        with pytest.raises(NetworkBlockedError):
            socket.getaddrinfo("example.com", 443)
    assert len(attempts) == 2
    assert socket.create_connection is original


def test_preflight_passes_offline_with_complete_settings() -> None:
    with block_network() as attempts:
        lines, problems = run_preflight(live_settings(enable_live_rag=False), env_file=None)

    assert problems == []
    assert attempts == []
    assert "Live clients constructed offline: yes" in lines
    assert "Live RAG active: False" in lines
    assert not any(DUMMY_KEY in line for line in lines)


def test_preflight_reports_missing_names_and_invalid_limits() -> None:
    settings = live_settings(gemini_api_key=None, final_context_chunks=20, retrieval_top_k=12)

    lines, problems = run_preflight(settings, env_file=None)

    assert "GEMINI_API_KEY is not set" in problems
    assert "FINAL_CONTEXT_CHUNKS must be between 1 and RETRIEVAL_TOP_K" in problems
    assert not any(DUMMY_KEY in line for line in lines + problems)


def test_duplicate_env_keys_reports_names_only(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nA=1\nexport B=secret-value\nA=2\nC=3\n", encoding="utf-8")

    assert duplicate_env_keys(env_file) == ["A"]
