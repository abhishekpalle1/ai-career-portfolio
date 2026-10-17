from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KB_DIR = REPO_ROOT / "knowledge-base"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "ingestion" / "state" / "manifest.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "ingestion" / "output"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class ConfigError(ValueError):
    pass


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer") from None


def _optional_env(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    chunk_size_tokens: int = 450
    chunk_overlap_tokens: int = 60
    embedding_model: str | None = None
    pinecone_index: str = "career-portfolio"
    pinecone_namespace: str = "production"
    enable_live_calls: bool = False
    openai_api_key: str | None = field(default=None, repr=False)
    pinecone_api_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.chunk_size_tokens <= 0:
            raise ConfigError("CHUNK_SIZE_TOKENS must be positive")
        if not 0 <= self.chunk_overlap_tokens < self.chunk_size_tokens:
            raise ConfigError("CHUNK_OVERLAP_TOKENS must be >= 0 and < CHUNK_SIZE_TOKENS")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        return cls(
            chunk_size_tokens=_int_env(env, "CHUNK_SIZE_TOKENS", 450),
            chunk_overlap_tokens=_int_env(env, "CHUNK_OVERLAP_TOKENS", 60),
            embedding_model=_optional_env(env, "OPENAI_EMBEDDING_MODEL"),
            pinecone_index=_optional_env(env, "PINECONE_INDEX") or "career-portfolio",
            pinecone_namespace=_optional_env(env, "PINECONE_NAMESPACE") or "production",
            enable_live_calls=env.get("ENABLE_LIVE_MODEL_CALLS", "").strip().lower()
            in _TRUE_VALUES,
            openai_api_key=_optional_env(env, "OPENAI_API_KEY"),
            pinecone_api_key=_optional_env(env, "PINECONE_API_KEY"),
        )

    def missing_live_requirements(self) -> list[str]:
        """Names (never values) of settings that block a live apply run."""
        missing: list[str] = []
        if not self.enable_live_calls:
            missing.append("ENABLE_LIVE_MODEL_CALLS=true")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.embedding_model:
            missing.append("OPENAI_EMBEDDING_MODEL")
        if not self.pinecone_api_key:
            missing.append("PINECONE_API_KEY")
        return missing

    def public_summary(self) -> dict[str, object]:
        return {
            "chunk_size_tokens": self.chunk_size_tokens,
            "chunk_overlap_tokens": self.chunk_overlap_tokens,
            "embedding_model": self.embedding_model,
            "pinecone_index": self.pinecone_index,
            "pinecone_namespace": self.pinecone_namespace,
            "enable_live_calls": self.enable_live_calls,
        }
