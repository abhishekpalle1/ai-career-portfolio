from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.mock_assistant import generate_mock_response

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a recruiter question.

    Phase 1 serves deterministic mock responses; retrieval and generation are
    introduced in Phase 3.
    """
    return generate_mock_response(request.message)
