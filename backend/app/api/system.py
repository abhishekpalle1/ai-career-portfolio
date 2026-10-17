from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.chat import HealthResponse, ReadyResponse, VersionResponse

router = APIRouter(tags=["system"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe. Never calls a paid dependency."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
def ready(settings: SettingsDep) -> ReadyResponse:
    """Readiness probe. Reports configuration presence without revealing values."""
    checks = {
        "cors_allowlist_configured": len(settings.frontend_origins) > 0,
        "corpus_version_configured": bool(settings.corpus_version),
        "input_limit_configured": settings.max_input_characters > 0,
        "live_rag_configuration_complete": (
            not settings.live_rag_enabled or not settings.missing_live_rag_settings()
        ),
    }
    return ReadyResponse(status="ready" if all(checks.values()) else "not_ready", checks=checks)


@router.get("/version", response_model=VersionResponse)
def version(settings: SettingsDep) -> VersionResponse:
    return VersionResponse(
        application_version=settings.app_version,
        corpus_version=settings.corpus_version,
        build_commit=settings.build_commit,
    )
