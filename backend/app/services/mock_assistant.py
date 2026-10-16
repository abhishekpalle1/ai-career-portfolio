"""Deterministic mock career assistant.

Phase 1 contains no retrieval and no model calls. This module returns fixed,
placeholder-based answers so the frontend can be built and tested against the
final API contract. It is replaced by the live RAG pipeline in Phase 3.

No answer here asserts a verified career fact: every claim is a bracketed
placeholder awaiting approved source content.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from app.models.chat import ChatResponse, Citation, Intent

ABSTENTION_ANSWER = (
    "I don't have approved source material covering that yet, so I can't answer it. "
    "The knowledge base is still being prepared. You can ask about Abhishek's "
    "professional experience, projects, skills, or education instead."
)

OUT_OF_SCOPE_ANSWER = (
    "I'm Abhishek's AI career portfolio assistant. I can answer questions about his "
    "documented professional experience, technical skills, portfolio projects, "
    "education, and role alignment."
)

OUT_OF_SCOPE_PATTERNS = (
    "ignore all previous",
    "ignore previous",
    "system prompt",
    "api key",
    "pinecone record",
    "write me a",
    "weather",
    "stock price",
)


@dataclass(frozen=True)
class MockAnswer:
    keywords: tuple[str, ...]
    intent: Intent
    answer: str
    citations: tuple[Citation, ...]
    suggested_questions: tuple[str, ...] = field(default=())


def _citation(
    citation_id: str,
    chunk_id: str,
    source_id: str,
    source_name: str,
    source_type: str,
    section: str,
    experience_type: str,
    source_url: str,
    excerpt: str,
) -> Citation:
    return Citation(
        citation_id=citation_id,
        chunk_id=chunk_id,
        source_id=source_id,
        source_name=source_name,
        source_type=source_type,  # type: ignore[arg-type]
        section=section,
        experience_type=experience_type,  # type: ignore[arg-type]
        source_url=source_url,
        excerpt=excerpt,
    )


MOCK_ANSWERS: tuple[MockAnswer, ...] = (
    MockAnswer(
        keywords=("worked", "employer", "companies", "where has"),
        intent="PROFESSIONAL_EXPERIENCE",
        answer=(
            "Approved employment history has not been loaded yet, so this is mock "
            "content illustrating the final answer format.\n"
            "- [EMPLOYER_1_NAME_TO_BE_PROVIDED] — [ROLE_TO_BE_PROVIDED], "
            "[DATE_RANGE_TO_BE_PROVIDED]\n"
            "- [EMPLOYER_2_NAME_TO_BE_PROVIDED] — [ROLE_TO_BE_PROVIDED], "
            "[DATE_RANGE_TO_BE_PROVIDED]"
        ),
        citations=(
            _citation(
                "C1",
                "resume-professional-experience-001",
                "resume-placeholder",
                "Resume (placeholder)",
                "RESUME",
                "Professional Experience",
                "PROFESSIONAL",
                "/resume.pdf",
                "[EXCERPT_TO_BE_PROVIDED] This excerpt is replaced by approved resume "
                "content during Phase 2 ingestion.",
            ),
        ),
        suggested_questions=(
            "What production AI systems has he built?",
            "Which technologies does he use?",
        ),
    ),
    MockAnswer(
        keywords=("production ai", "systems has he built", "built", "project"),
        intent="PROJECT_DETAILS",
        answer=(
            "Approved project content has not been loaded yet. This mock answer shows how "
            "professional systems and portfolio projects are kept separate.\n"
            "- [PRODUCTION_AI_SYSTEM_TITLE_TO_BE_PROVIDED] — professional work at "
            "[EMPLOYER_1_NAME_TO_BE_PROVIDED]\n"
            "- AI Career Portfolio and Resume RAG Assistant — personal portfolio project, "
            "not an employer deployment"
        ),
        citations=(
            _citation(
                "C1",
                "project-portfolio-rag-001",
                "portfolio-rag-placeholder",
                "AI Career Portfolio project notes (placeholder)",
                "PORTFOLIO_PROJECT",
                "Project Overview",
                "PORTFOLIO",
                "/projects/ai-career-portfolio",
                "[EXCERPT_TO_BE_PROVIDED] A React and FastAPI portfolio assistant built as "
                "a personal project. Not deployed for any employer.",
            ),
        ),
        suggested_questions=(
            "What is his experience with RAG and LLM evaluation?",
            "Where has Abhishek worked?",
        ),
    ),
    MockAnswer(
        keywords=("rag", "llm evaluation", "evaluation"),
        intent="SKILL_EVIDENCE",
        answer=(
            "Approved skills evidence has not been loaded yet. Once the knowledge base is "
            "ingested, this answer will summarise documented retrieval-augmented generation "
            "and evaluation work with citations.\n"
            "- [RAG_EVIDENCE_TO_BE_PROVIDED]\n"
            "- [EVALUATION_EVIDENCE_TO_BE_PROVIDED]"
        ),
        citations=(
            _citation(
                "C1",
                "skills-evidence-rag-001",
                "skills-placeholder",
                "Skills evidence (placeholder)",
                "SKILLS_EVIDENCE",
                "Retrieval and Evaluation",
                "GENERAL",
                "/skills",
                "[EXCERPT_TO_BE_PROVIDED] Replaced by approved skills evidence in Phase 2.",
            ),
        ),
        suggested_questions=(
            "What production AI systems has he built?",
            "What is his educational background?",
        ),
    ),
    MockAnswer(
        keywords=("technolog", "tools", "stack", "languages"),
        intent="TECHNOLOGY_EXPERIENCE",
        answer=(
            "Approved technology evidence has not been loaded yet. The technologies listed "
            "below are drawn only from this portfolio project.\n"
            "- Frontend: React, TypeScript, Vite\n"
            "- Backend: Python, FastAPI, Pydantic\n"
            "- Testing: Pytest, Vitest"
        ),
        citations=(
            _citation(
                "C1",
                "project-portfolio-rag-stack-001",
                "portfolio-rag-placeholder",
                "AI Career Portfolio project notes (placeholder)",
                "PORTFOLIO_PROJECT",
                "Technology Stack",
                "PORTFOLIO",
                "/projects/ai-career-portfolio",
                "[EXCERPT_TO_BE_PROVIDED] React, TypeScript, Vite, FastAPI, and Pydantic are "
                "used in this portfolio project.",
            ),
        ),
        suggested_questions=(
            "What production AI systems has he built?",
            "Where has Abhishek worked?",
        ),
    ),
    MockAnswer(
        keywords=("education", "degree", "university", "certification"),
        intent="EDUCATION_CERTIFICATIONS",
        answer=(
            "Approved education records have not been loaded yet, so no degree, institution, "
            "or certification is asserted here.\n"
            "- [DEGREE_TO_BE_PROVIDED], [INSTITUTION_TO_BE_PROVIDED], "
            "[GRADUATION_YEAR_TO_BE_PROVIDED]"
        ),
        citations=(
            _citation(
                "C1",
                "education-001",
                "education-placeholder",
                "Education record (placeholder)",
                "EDUCATION",
                "Education",
                "EDUCATION",
                "/education",
                "[EXCERPT_TO_BE_PROVIDED] Replaced by approved education content in Phase 2.",
            ),
        ),
        suggested_questions=(
            "Which technologies does he use?",
            "What is his experience with RAG and LLM evaluation?",
        ),
    ),
)

DEFAULT_SUGGESTIONS: tuple[str, ...] = (
    "Where has Abhishek worked?",
    "What production AI systems has he built?",
)


def normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message).strip().lower()


def generate_mock_response(message: str) -> ChatResponse:
    """Return a deterministic mock answer for the supplied question."""
    normalized = normalize(message)
    trace_id = uuid.uuid4().hex[:16]

    if any(pattern in normalized for pattern in OUT_OF_SCOPE_PATTERNS):
        return ChatResponse(
            answer=OUT_OF_SCOPE_ANSWER,
            citations=[],
            suggested_questions=list(DEFAULT_SUGGESTIONS),
            intent="OUT_OF_SCOPE",
            grounded=False,
            abstained=True,
            trace_id=trace_id,
        )

    for candidate in MOCK_ANSWERS:
        if any(keyword in normalized for keyword in candidate.keywords):
            return ChatResponse(
                answer=candidate.answer,
                citations=list(candidate.citations),
                suggested_questions=list(candidate.suggested_questions),
                intent=candidate.intent,
                grounded=True,
                abstained=False,
                trace_id=trace_id,
            )

    return ChatResponse(
        answer=ABSTENTION_ANSWER,
        citations=[],
        suggested_questions=list(DEFAULT_SUGGESTIONS),
        intent="PROFILE_SUMMARY",
        grounded=False,
        abstained=True,
        trace_id=trace_id,
    )
