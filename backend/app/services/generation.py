from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.prompts.grounded_answer import SYSTEM_PROMPT, render_user_input
from app.retrieval.vector_store import RetrievedChunk

SupportLevel = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"]
ClaimExperienceType = Literal["PROFESSIONAL", "PORTFOLIO", "EDUCATION", "GENERAL"]


# Strict structured-output schema: every field required, no defaults.
class GeneratedClaim(BaseModel):
    text: str
    citation_ids: list[str]
    support_level: SupportLevel
    experience_type: ClaimExperienceType


class GeneratedAnswer(BaseModel):
    answer: str
    claims: list[GeneratedClaim]
    citation_ids: list[str]
    grounded: bool
    abstained: bool
    abstention_reason: str | None
    suggested_questions: list[str]


class AnswerGenerator(Protocol):
    def generate(self, question: str, context: list[RetrievedChunk]) -> GeneratedAnswer | None: ...


class GeminiAnswerGenerator:
    def __init__(self, client: Any, model: str, max_output_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens

    @classmethod
    def from_settings(cls, settings: Settings, client: Any) -> GeminiAnswerGenerator:
        return cls(client, settings.gemini_generation_model, settings.gemini_max_output_tokens)

    def generate(self, question: str, context: list[RetrievedChunk]) -> GeneratedAnswer | None:
        """Returns None when the model returns no text or output that fails the schema."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=render_user_input(question, context),
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "response_json_schema": GeneratedAnswer.model_json_schema(),
                "max_output_tokens": self._max_output_tokens,
                "automatic_function_calling": {"disable": True},
            },
        )
        text = response.text
        if not text:
            return None
        try:
            return GeneratedAnswer.model_validate_json(text)
        except ValidationError:
            return None
