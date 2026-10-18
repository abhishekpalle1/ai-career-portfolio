from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.prompts.grounded_answer import SYSTEM_PROMPT, render_user_input
from app.retrieval.vector_store import RetrievedChunk

SupportLevel = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"]
ClaimExperienceType = Literal["PROFESSIONAL", "PORTFOLIO", "EDUCATION", "GENERAL"]


# Strict structured-output schema: every field required, no defaults. Bounds keep the complete
# JSON inside GEMINI_MAX_OUTPUT_TOKENS; Gemini enforces maxItems, Pydantic enforces the rest.
class GeneratedClaim(BaseModel):
    text: str = Field(max_length=300)
    citation_ids: list[str] = Field(max_length=5)
    support_level: SupportLevel
    experience_type: ClaimExperienceType


class GeneratedAnswer(BaseModel):
    answer: str = Field(max_length=1500)
    claims: list[GeneratedClaim] = Field(max_length=3)
    citation_ids: list[str] = Field(max_length=5)
    grounded: bool
    abstained: bool
    abstention_reason: str | None = Field(max_length=300)
    suggested_questions: list[str] = Field(max_length=2)


def response_schema() -> dict[str, Any]:
    """JSON schema sent to Gemini, without string-length keywords its schema subset omits."""

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k != "maxLength"}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    schema: dict[str, Any] = strip(GeneratedAnswer.model_json_schema())
    return schema


class AnswerGenerator(Protocol):
    def generate(self, question: str, context: list[RetrievedChunk]) -> GeneratedAnswer | None: ...


class GeminiAnswerGenerator:
    def __init__(self, client: Any, model: str, max_output_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens
        self.last_usage: dict[str, int] = {}

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
                "response_json_schema": response_schema(),
                "max_output_tokens": self._max_output_tokens,
                "automatic_function_calling": {"disable": True},
            },
        )
        usage = getattr(response, "usage_metadata", None)
        self.last_usage = {
            "input_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
            "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
            "thinking_tokens": int(getattr(usage, "thoughts_token_count", 0) or 0),
        }
        text = response.text
        if not text:
            return None
        try:
            return GeneratedAnswer.model_validate_json(text)
        except ValidationError:
            return None
