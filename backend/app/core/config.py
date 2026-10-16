from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Module-level default so Pydantic request models can bound `message` length
# without importing runtime settings at class-definition time.
DEFAULT_MAX_INPUT_CHARACTERS = 500


class Settings(BaseSettings):
    """Environment-driven application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    build_commit: str = "local"

    # NoDecode suppresses JSON parsing so the comma-separated validator sees the raw string.
    frontend_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    corpus_version: str = "2026-10"
    max_input_characters: int = DEFAULT_MAX_INPUT_CHARACTERS

    enable_live_model_calls: bool = False

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
