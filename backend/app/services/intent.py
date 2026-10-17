"""Deterministic intent classification. No model call; never affects retrieval filters."""

from __future__ import annotations

import re

from app.models.chat import Intent

_RULES: tuple[tuple[Intent, re.Pattern[str]], ...] = (
    (
        "OUT_OF_SCOPE",
        re.compile(
            r"ignore (all )?(previous|prior)|system prompt|api key|pinecone record"
            r"|write me a|weather|stock price"
        ),
    ),
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
    (
        "EDUCATION_CERTIFICATIONS",
        re.compile(
            r"\b(educat\w*|degree|universit\w*|college|gpa|certif\w*|master'?s|bachelor'?s|studied)\b"
        ),
    ),
    (
        "ROLE_FIT",
        re.compile(r"\b(good fit|fit for|suitable|qualified|why hire|strong candidate)\b"),
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
        re.compile(r"\b(technolog\w*|tools?|stack|languages?|frameworks?|cloud|gcp|python)\b"),
    ),
    (
        "SKILL_EVIDENCE",
        re.compile(r"\b(skills?|rag|evaluation|llms?|genai|machine learning|expertise)\b"),
    ),
    (
        "PROFESSIONAL_EXPERIENCE",
        re.compile(r"\b(work(ed)?|employers?|compan(y|ies)|jobs?|career|roles?|intern\w*)\b"),
    ),
)


def normalize_question(message: str) -> str:
    return re.sub(r"\s+", " ", message).strip().lower()


def classify_intent(message: str) -> Intent:
    normalized = normalize_question(message)
    for intent, pattern in _RULES:
        if pattern.search(normalized):
            return intent
    return "PROFILE_SUMMARY"
