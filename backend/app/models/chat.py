from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import DEFAULT_MAX_INPUT_CHARACTERS

ExperienceType = Literal["PROFESSIONAL", "PORTFOLIO", "EDUCATION", "GENERAL"]

SourceType = Literal[
    "RESUME",
    "PROFESSIONAL_PROFILE",
    "PROFESSIONAL_EXPERIENCE",
    "PORTFOLIO_PROJECT",
    "SKILLS_EVIDENCE",
    "EDUCATION",
    "CERTIFICATION",
    "RECRUITER_FAQ",
    "PUBLIC_CONTACT",
]

Intent = Literal[
    "PROFILE_SUMMARY",
    "PROFESSIONAL_EXPERIENCE",
    "PROJECT_DETAILS",
    "SKILL_EVIDENCE",
    "TECHNOLOGY_EXPERIENCE",
    "ROLE_FIT",
    "BUSINESS_IMPACT",
    "EDUCATION_CERTIFICATIONS",
    "CONTACT_INFORMATION",
    "RESUME_REQUEST",
    "OUT_OF_SCOPE",
]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=DEFAULT_MAX_INPUT_CHARACTERS)
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class Citation(BaseModel):
    citation_id: str
    chunk_id: str
    source_id: str
    source_name: str
    source_type: SourceType
    section: str
    experience_type: ExperienceType
    source_url: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    suggested_questions: list[str]
    intent: Intent
    grounded: bool
    abstained: bool
    trace_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]


class VersionResponse(BaseModel):
    application_version: str
    corpus_version: str
    build_commit: str
