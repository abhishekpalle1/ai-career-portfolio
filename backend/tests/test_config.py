"""Configuration parsing tests.

These cover the gap that let a `.env` file crash application startup: the test
suite previously only ever constructed `Settings` with built-in defaults.
"""

from pathlib import Path

import pytest

from app.core.config import DEFAULT_MAX_INPUT_CHARACTERS, Settings, get_settings


def _settings_without_dotenv() -> Settings:
    """Build settings ignoring any local .env so tests stay hermetic."""
    return Settings(_env_file=None)


def test_defaults_are_usable_without_any_env_file() -> None:
    settings = _settings_without_dotenv()

    assert settings.frontend_origins == ["http://localhost:5173"]
    assert settings.max_input_characters == DEFAULT_MAX_INPUT_CHARACTERS
    assert settings.enable_live_model_calls is False


def test_comma_separated_origins_parse_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

    assert _settings_without_dotenv().frontend_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_single_origin_parses_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://example.github.io")

    assert _settings_without_dotenv().frontend_origins == ["https://example.github.io"]


def test_origins_tolerate_whitespace_and_empty_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", " http://a.test , http://b.test ,, ")

    assert _settings_without_dotenv().frontend_origins == [
        "http://a.test",
        "http://b.test",
    ]


def test_settings_load_from_a_dotenv_file(tmp_path: Path) -> None:
    """Regression: a .env with comma-separated origins must not raise."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=production\n"
        "FRONTEND_ORIGINS=http://localhost:5173,https://example.github.io\n"
        "MAX_INPUT_CHARACTERS=250\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.frontend_origins == [
        "http://localhost:5173",
        "https://example.github.io",
    ]
    assert settings.max_input_characters == 250
    assert settings.is_production is True


def test_shipped_env_example_parses(tmp_path: Path) -> None:
    """The committed .env.example must be directly copyable to .env."""
    example = Path(__file__).resolve().parents[1] / ".env.example"
    target = tmp_path / ".env"
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")

    settings = Settings(_env_file=target)

    assert settings.frontend_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert settings.enable_live_model_calls is False
    assert settings.corpus_version == "2026-10"


def test_is_production_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "PRODUCTION")

    assert _settings_without_dotenv().is_production is True


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_live_rag_requires_both_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_RAG", "true")
    assert _settings_without_dotenv().live_rag_enabled is False

    monkeypatch.setenv("ENABLE_LIVE_MODEL_CALLS", "true")
    assert _settings_without_dotenv().live_rag_enabled is True


def test_empty_optional_values_fall_back_to_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MIN_RETRIEVAL_SCORE=\nMAX_CONTEXT_TOKENS=\nGEMINI_EMBEDDING_DIMENSIONS=\nGEMINI_API_KEY=\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.min_retrieval_score is None
    assert settings.max_context_tokens is None
    assert settings.gemini_embedding_dimensions is None
    assert settings.gemini_api_key is None
    assert "GEMINI_API_KEY" in settings.missing_live_rag_settings()
    assert "GEMINI_EMBEDDING_DIMENSIONS" in settings.missing_live_rag_settings()


def test_openai_settings_are_not_required_or_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai-value")

    settings = _settings_without_dotenv()

    assert not any(name.startswith("OPENAI") for name in settings.missing_live_rag_settings())
    assert "dummy-openai-value" not in str(settings.model_dump())


def test_secrets_are_hidden_from_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-secret-value-123")
    monkeypatch.setenv("PINECONE_API_KEY", "dummy-secret-value-456")

    settings = _settings_without_dotenv()

    assert "dummy-secret-value" not in repr(settings)
    assert "dummy-secret-value" not in str(settings.model_dump())
