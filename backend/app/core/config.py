from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Module-level default so Pydantic request models can bound `message` length
# without importing runtime settings at class-definition time.
DEFAULT_MAX_INPUT_CHARACTERS = 500


class Settings(BaseSettings):
    """Environment-driven application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    app_env: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    build_commit: str = "local"

    # NoDecode suppresses JSON parsing so the comma-separated validator sees the raw string.
    frontend_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    corpus_version: str = "2026-10"
    max_input_characters: int = DEFAULT_MAX_INPUT_CHARACTERS

    enable_live_model_calls: bool = False
    enable_live_rag: bool = False

    gemini_api_key: SecretStr | None = None
    gemini_embedding_model: str = ""
    # Must match the value used at ingestion time and the Pinecone index dimension.
    gemini_embedding_dimensions: int | None = None
    gemini_generation_model: str = ""
    gemini_max_output_tokens: int = 800
    pinecone_api_key: SecretStr | None = None
    pinecone_index: str = "career-portfolio"
    pinecone_namespace: str = "production"
    external_timeout_seconds: float = 15.0

    retrieval_top_k: int = 12
    final_context_chunks: int = 5
    # Unset until established by evaluation (Phase 5).
    min_retrieval_score: float | None = None
    max_context_tokens: int | None = None

    # Phase 4 cost and abuse controls. In-memory state assumes a single instance (Cloud Run max 1).
    max_questions_per_session: int = 10
    max_questions_per_ip_per_day: int = 20
    # Number of trusted proxies in front of the app; 0 ignores X-Forwarded-For entirely.
    trusted_proxy_hops: int = 0
    cache_ttl_seconds: int = 3600
    cache_max_entries: int = 500
    max_generation_retries: int = 0
    max_answer_characters: int = 1500

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def live_rag_enabled(self) -> bool:
        return self.enable_live_rag and self.enable_live_model_calls

    def missing_live_rag_settings(self) -> list[str]:
        """Names (never values) of settings the live RAG path cannot run without."""
        required = {
            "GEMINI_API_KEY": self.gemini_api_key is not None,
            "GEMINI_EMBEDDING_MODEL": bool(self.gemini_embedding_model),
            "GEMINI_EMBEDDING_DIMENSIONS": self.gemini_embedding_dimensions is not None,
            "GEMINI_GENERATION_MODEL": bool(self.gemini_generation_model),
            "PINECONE_API_KEY": self.pinecone_api_key is not None,
            "PINECONE_INDEX": bool(self.pinecone_index),
            "PINECONE_NAMESPACE": bool(self.pinecone_namespace),
        }
        return [name for name, present in required.items() if not present]


@lru_cache
def get_settings() -> Settings:
    return Settings()
