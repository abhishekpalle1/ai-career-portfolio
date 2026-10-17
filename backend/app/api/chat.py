import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import Settings, get_settings
from app.guardrails.cost_controls import RateLimiter
from app.models.chat import ChatRequest, ChatResponse
from app.services.mock_assistant import generate_mock_response
from app.services.rag_assistant import UNAVAILABLE_MESSAGE, AssistantUnavailableError, RagAssistant

logger = logging.getLogger("career-portfolio.chat")

router = APIRouter(prefix="/api/v1", tags=["chat"])

RATE_LIMIT_MESSAGE = (
    "You've reached the question limit for now. You can still explore Abhishek's experience, "
    "projects, skills, and resume on this page."
)

Assistant = Callable[[str], ChatResponse]
SettingsDep = Annotated[Settings, Depends(get_settings)]

_live_cache: tuple[Settings, RagAssistant] | None = None
_limiter: tuple[tuple[int, int], RateLimiter] | None = None


def get_rate_limiter(settings: SettingsDep) -> RateLimiter:
    global _limiter
    limits = (settings.max_questions_per_session, settings.max_questions_per_ip_per_day)
    if _limiter is None or _limiter[0] != limits:
        _limiter = (
            limits,
            RateLimiter(max_per_session=limits[0], max_per_ip_per_day=limits[1]),
        )
    return _limiter[1]


def client_ip(request: Request, trusted_proxy_hops: int) -> str:
    """Each trusted proxy appends one X-Forwarded-For entry; earlier ones are client-supplied."""
    if trusted_proxy_hops > 0:
        forwarded = [
            part.strip()
            for part in request.headers.get("x-forwarded-for", "").split(",")
            if part.strip()
        ]
        if len(forwarded) >= trusted_proxy_hops:
            return forwarded[-trusted_proxy_hops]
    return request.client.host if request.client else "unknown"


def _live_assistant(settings: Settings) -> RagAssistant:
    global _live_cache
    if _live_cache is None or _live_cache[0] is not settings:
        _live_cache = (settings, RagAssistant.from_settings(settings))
    return _live_cache[1]


def get_assistant(settings: SettingsDep) -> Assistant:
    """Mock answers unless both ENABLE_LIVE_RAG and ENABLE_LIVE_MODEL_CALLS are true."""
    if not settings.live_rag_enabled:
        return generate_mock_response
    try:
        return _live_assistant(settings).answer
    except AssistantUnavailableError as exc:
        logger.error("Live RAG unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=UNAVAILABLE_MESSAGE) from None


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    http_request: Request,
    settings: SettingsDep,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    assistant: Annotated[Assistant, Depends(get_assistant)],
) -> ChatResponse:
    """Answer a recruiter question from approved, retrieved evidence."""
    decision = limiter.check_and_record(
        client_ip(http_request, settings.trusted_proxy_hops), request.session_id
    )
    if not decision.allowed:
        logger.info("rate_limited reason=%s", decision.reason)
        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE,
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    try:
        return assistant(request.message)
    except AssistantUnavailableError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_MESSAGE) from None
