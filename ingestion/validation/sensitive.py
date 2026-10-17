from __future__ import annotations

import re
from dataclasses import dataclass

from ingestion.models import Finding


@dataclass(frozen=True)
class _Rule:
    code: str
    pattern: re.Pattern[str]
    message: str


_RULES = (
    _Rule(
        "PRIVATE_KEY",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "Private key material",
    ),
    _Rule(
        "API_KEY",
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_-]{20,}|pcsk_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
            r"|gh[pousr]_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{35})"
        ),
        "API key or access token",
    ),
    _Rule(
        "CREDENTIAL_ASSIGNMENT",
        re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token)\s*[:=]\s*\S+"),
        "Credential-like assignment",
    ),
    _Rule(
        "PHONE_NUMBER",
        re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"),
        "Phone number",
    ),
    _Rule(
        "REDACTION_PLACEHOLDER",
        re.compile(r"\[REDACTED[A-Z_]*\]"),
        "Unresolved redaction placeholder",
    ),
    _Rule(
        "INTERNAL_URL",
        re.compile(
            r"(?i)\bhttps?://(?:localhost|127(?:\.\d{1,3}){3}|10(?:\.\d{1,3}){3}"
            r"|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
            r"|[^\s/]+\.(?:internal|local|corp|intranet|lan))(?![\w.-])"
        ),
        "Internal or private-network URL",
    ),
    _Rule(
        "CONFIDENTIALITY_MARKER",
        re.compile(r"(?i)\b(?:confidential|internal use only|do not distribute)\b"),
        "Confidentiality marker",
    ),
    _Rule(
        "EMBEDDED_INSTRUCTION",
        re.compile(
            r"(?i)\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?"
            r"(?:previous|prior|above|earlier)\s+instructions\b|\byou are now\b"
        ),
        "Embedded instruction aimed at the assistant",
    ),
)

_EMAIL_RULE = _Rule(
    "EMAIL_ADDRESS",
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "Email address",
)


def scan_sensitive_content(text: str, *, allow_email: bool = False) -> list[Finding]:
    """Report sensitive-content categories by line. Matched values are never included."""
    rules = _RULES if allow_email else (*_RULES, _EMAIL_RULE)
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in rules:
            if rule.pattern.search(line):
                findings.append(Finding("ERROR", rule.code, rule.message, line_number))
    return findings
