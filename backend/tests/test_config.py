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
