from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.core.config import Settings, get_settings
from app.main import app

# Cleared for every test so the suite never reads real keys or live flags.
LIVE_ENV_VARS = (
    "ENABLE_LIVE_MODEL_CALLS",
    "ENABLE_LIVE_RAG",
    "ENABLE_LIVE_VECTOR_UPSERTS",
    "GEMINI_API_KEY",
    "GEMINI_EMBEDDING_MODEL",
    "GEMINI_EMBEDDING_DIMENSIONS",
    "GEMINI_GENERATION_MODEL",
    "GEMINI_MAX_OUTPUT_TOKENS",
    "PINECONE_API_KEY",
    "PINECONE_INDEX",
    "PINECONE_NAMESPACE",
    "MAX_QUESTIONS_PER_SESSION",
    "MAX_QUESTIONS_PER_IP_PER_DAY",
    "TRUSTED_PROXY_HOPS",
    "CACHE_TTL_SECONDS",
    "CACHE_MAX_ENTRIES",
    "MAX_GENERATION_RETRIES",
    "MAX_ANSWER_CHARACTERS",
)


@pytest.fixture(autouse=True)
def hermetic_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in LIVE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(chat_module, "_limiter", None)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
