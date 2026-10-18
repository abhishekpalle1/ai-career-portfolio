"""Deterministic intent and scope routing. No model call; never affects retrieval filters.

Runs only on input that passed the security input guard. OUT_OF_SCOPE ends the request before
any paid call; every other intent continues to bounded RAG.
"""

from __future__ import annotations

import re

from app.models.chat import Intent

# Defense in depth behind the security input guard.
_SECURITY_OUT_OF_SCOPE = re.compile(
    r"ignore (all )?(previous|prior)|\b(your|the) system prompt|api key|pinecone record"
)
_REQUEST = r"^(please\s+|can you\s+|could you\s+|help me\s+|now\s+)?"
# Unrelated tasks are out of scope even when the request mentions him.
_UNRELATED_TASK = re.compile(
    _REQUEST + r"(write|generate|create|implement|code|debug|fix)\b.{0,40}?"
    r"\b(code|function|script|program|algorithm|class|regex|sql query|essay|poem|story|song"
    r"|joke|haiku)\b"
    r"|" + _REQUEST + r"(solve|calculate|compute|simplify|translate)\b"
    r"|\b(investment|financial|legal|medical|tax|relationship) advice\b"
)
# Everyday subjects are out of scope unless the question is anchored to his career.
_UNRELATED_TOPIC = re.compile(
    r"\b(weather|stock prices?|horoscope|lottery|recipes?|sports? scores?|movies?|celebrit\w*)\b"
)

_PROFILE_SUMMARY = re.compile(
    r"\btell me about (abhishek|palle|him|the candidate|his (background|career))\b"
    r"|\bwho is (abhishek|palle|he|the candidate)\b"
    r"|\boverview of (abhishek|palle|him|his)\b"
    r"|\bsummar\w* (of )?(his|abhishek'?s?|palle'?s?) (background|career|profile|experience)\b"
    r"|\b(professional|career) (summary|background|overview|profile)\b"
    r"|\bsummary of (abhishek|palle|him)\b|\byears of experience\b|\bhow (experienced|senior)\b"
)

_RULES: tuple[tuple[Intent, re.Pattern[str]], ...] = (
    (
        "CONTACT_INFORMATION",
        re.compile(
            r"\b(contact|e-?mail|phone|reach (him|abhishek)|get in touch|linkedin|github)\b"
        ),
    ),
    (
        "RESUME_REQUEST",
        re.compile(
            r"\b(download|send|share|link|copy|view|see|open)\b.*\b(resume|r[eé]sum[eé]|cv)\b"
        ),
    ),
    ("PROFILE_SUMMARY", _PROFILE_SUMMARY),
    (
        "EDUCATION_CERTIFICATIONS",
        re.compile(
            r"\b(educat\w*|degree|universit\w*|college|gpa|certif\w*|master'?s|bachelor'?s|studied"
            r"|study|undergrad\w*|graduat\w*|school)\b"
        ),
    ),
    (
        "ROLE_FIT",
        re.compile(r"\b(fit|good fit|fit for|suitable|qualified|why hire|strong candidate)\b"),
    ),
    (
        "BUSINESS_IMPACT",
        re.compile(r"\b(impact|metrics?|results?|outcomes?|roi|improv\w*|saved|savings)\b"),
    ),
    (
        "PROJECT_DETAILS",
        re.compile(r"\b(projects?|built|build|systems?|platforms?|initiatives?)\b"),
    ),
    (
        "TECHNOLOGY_EXPERIENCE",
        re.compile(
            r"\b(technolog\w*|tools?|stack|languages?|frameworks?|cloud|gcp|python|pytorch"
            r"|tensorflow|computer vision|mlops|orchestration|vertex|bigquery|spark|sql"
            r"|kubernetes|docker)\b"
        ),
    ),
    (
        "SKILL_EVIDENCE",
        re.compile(r"\b(skills?|rag|evaluation|llms?|genai|machine learning|expertise)\b"),
    ),
    (
        "PROFESSIONAL_EXPERIENCE",
        re.compile(
            r"\b(work(ed)?|employers?|employ\w*|compan(y|ies)|jobs?|career|roles?|intern\w*"
            r"|positions?)\b|\b(do|did) at\b"
        ),
    ),
)

# Signals that a question concerns the candidate or his documented domain.
_CAREER_ANCHOR = re.compile(
    r"\b(abhishek|palle|he|him|his|candidate|resume|r[eé]sum[eé]|cv|portfolio|experience"
    r"|team|lead\w*|manag\w*|deploy\w*|production|pipelines?|models?|classif\w*|claims?"
    r"|fraud|underwrit\w*|insurance|pricing|forecast\w*|anomal\w*|robotics|vision|nlp|bert"
    r"|ai|ml|data|analytics|agents?|agentic|prompts?|retrieval|cna|stanley|black & decker"
    r"|eternal|production modeling|workers'? comp\w*|commercial auto)\b"
)
_FOLLOW_UP = re.compile(
    r"^(and |also |so |ok(ay)?,? )?(what|how) about\b|\btell me more\b|\bmore (details?|about)\b"
    r"|\b(which|that|this|the other|the same) ones?\b|^(and|also)\b"
    r"|^(why|how so|go on|continue|elaborate)\W*$"
)
# A complete general question or command with no career anchor is unrelated.
_GENERAL_QUESTION = re.compile(
    r"^(what|who|whom|whose|when|where|which|why|how|is|are|was|were|do|does|did|can|could"
    r"|would|will|should|explain|define|describe|name|list|tell me|give me|show me)\b"
)
_EMPLOYER_HISTORY = re.compile(
    r"\bwhere (has|have|did|does) (he|abhishek|palle)( \w+)? work"
    r"|\b(employers?|employment history|work history|career history)\b|\bcompanies\b"
    r"|\b(first|previous|past|prior|earlier) (jobs?|roles?|employers?)\b|\binternships?\b"
    r"|\bwho (has|did) (he|abhishek) work(ed)? for\b"
)


def normalize_question(message: str) -> str:
    return re.sub(r"\s+", " ", message).strip().lower()


def classify_intent(message: str) -> Intent:
    normalized = normalize_question(message)
    anchored = bool(_CAREER_ANCHOR.search(normalized))
    if _SECURITY_OUT_OF_SCOPE.search(normalized) or _UNRELATED_TASK.search(normalized):
        return "OUT_OF_SCOPE"
    if _UNRELATED_TOPIC.search(normalized) and not anchored:
        return "OUT_OF_SCOPE"
    for intent, pattern in _RULES:
        if pattern.search(normalized):
            return intent
    if anchored or _FOLLOW_UP.search(normalized):
        return "PROFILE_SUMMARY"
    if _GENERAL_QUESTION.search(normalized):
        return "OUT_OF_SCOPE"
    # Fragments such as "Pricing?" are treated as plausible follow-ups, not blocked.
    return "PROFILE_SUMMARY"


def wants_employer_history(message: str) -> bool:
    """Broad questions about where he has worked, as opposed to one employer or project."""
    return bool(_EMPLOYER_HISTORY.search(normalize_question(message)))
