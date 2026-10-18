"""Deterministic input guardrails. Runs before any paid call; never calls a model."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote

PROMPT_INJECTION = "PROMPT_INJECTION"
CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
DATA_EXFILTRATION = "DATA_EXFILTRATION"
FABRICATION_REQUEST = "FABRICATION_REQUEST"
SENSITIVE_PERSONAL_DATA = "SENSITIVE_PERSONAL_DATA"
CONFIDENTIAL_EMPLOYER = "CONFIDENTIAL_EMPLOYER"
UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
ENCODED_PAYLOAD = "ENCODED_PAYLOAD"
OUT_OF_SCOPE_TASK = "OUT_OF_SCOPE_TASK"

_ZERO_WIDTH_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00ad]")
_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)

# Prompt-attack detection; any match in any family is PROMPT_INJECTION. contains_injection() also
# screens retrieved chunks, so résumé terms alone (prompt engineering, prompts, instructions,
# configuration, programming, guardrails) must never match: patterns need an attack verb or a
# reference to the assistant itself. Overlap between families is intentional and harmless.

# Manipulation: override, bypass, or replace the assistant's governing behavior (jailbreaks,
# role replacement, injected instructions).
INJECTION_PATTERNS = (
    re.compile(
        r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}?"
        r"\b(previous|prior|above|earlier|all|your|system|these|any)\b.{0,20}?"
        r"\b(instructions?|rules?|prompts?|guidelines?|directions?|polic(y|ies))\b"
    ),
    re.compile(
        r"\byou are now\b|\bpretend (to be|you are)\b|\bdeveloper mode\b|\bjailbreak\w*\b"
        r"|\bdo anything now\b|\bdan mode\b|\bno (restrictions|rules|filters)\b|\bunfiltered\b"
        r"|\bnew instructions?\b|\bfrom now on\b|\brole[- ]?play\b"
    ),
)

_ASSISTANT = r"(you|the assistant|this assistant|the bot|the chatbot|the ai|the model)"
_DIRECTIVES = (
    r"(instructions?|rules?|guidelines?|directions?|directives?|prompts?|guardrails?"
    r"|programming|configuration)"
)
# Extraction: discover, reproduce, quote, or reveal the assistant's hidden, system, or developer
# instructions, or privileged content that preceded the user's message.
EXTRACTION_PATTERNS = (
    re.compile(
        r"\b(your|(the|this) assistant( s)?)\s+"
        r"(system|hidden|initial|original|developer)\s+(prompt|instructions?|message)\b"
        r"|\b(hidden|initial|original)\s+(prompt|instructions)\b"
    ),
    re.compile(
        r"\b(reveal|show|print|repeat|display|dump|output|leak)\b.{0,30}?"
        r"\b(your|the|system|hidden|internal)\s+(prompt|instructions|system message|guardrails)\b"
    ),
    re.compile(
        r"\b(repeat|print|output|show|reveal|copy)\b.{0,25}?"
        r"\b(text|everything|words|content|message)\s+(above|before|preceding)\b"
    ),
    re.compile(
        r"\b(reveal|show|print|repeat|display|dump|output|copy|quote|recite|leak)\b.{0,30}?"
        r"\b(preceding|previous|prior|above|earlier|initial|first)\s+(system\s+|developer\s+)?"
        r"(messages?|prompts?|instructions?|text|content)\b"
    ),
    re.compile(
        rf"\b(what|which)\s+{_DIRECTIVES}\s+(were|was|have|has|did|do|does|are)\s+{_ASSISTANT}\b"
    ),
    re.compile(
        rf"\b{_DIRECTIVES}\s+(that\s+)?{_ASSISTANT}\s+"
        r"(were|was|have|had|are|got|received?|follows?|followed|use)\b"
    ),
    re.compile(
        r"\b(quote|repeat|recite|reveal|show|print|tell|give|list|share|provide|output|display"
        r"|state|paste|copy|dump|read|write|send)\b(\s+\w+){0,3}?"
        rf"\s+(your|the assistant s|this assistant s|its)\s+(\w+\s+){{0,3}}?{_DIRECTIVES}\b"
    ),
    re.compile(
        r"\bwhat\s+(were|are|have)\s+you\s+(been\s+)?"
        r"(told|instructed|programmed|configured|asked|directed|trained)\b"
        r"|\bwhat\s+you\s+(were|are|have been)\s+"
        r"(told|instructed|programmed|configured|asked|directed)\b"
    ),
)

# Normalization-resistant markers for high-confidence attacks, matched after removing spacing,
# punctuation, and leetspeak (e.g. "i.g.n.o.r.e prev1ous instructions").
_SQUASHED_INJECTION = (
    "ignorepreviousinstructions",
    "ignoreallpreviousinstructions",
    "ignoreallinstructions",
    "ignoreyourinstructions",
    "disregardpreviousinstructions",
    "revealyoursystemprompt",
    "showyoursystemprompt",
    "printyoursystemprompt",
    "jailbreak",
    "revealyourprompt",
)

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        CREDENTIAL_REQUEST,
        re.compile(
            r"\b(api|access|secret|private)[\s_-]*keys?\b|\bpasswords?\b"
            r"|\b(api|auth|access|bearer)\s+tokens?\b|\benv(ironment)?\s+var(iable)?s?\b"
            r"|(^|\s)\.env\b|\bsecret manager\b|\blogin credentials\b"
        ),
    ),
    (
        DATA_EXFILTRATION,
        re.compile(
            r"\b(dump|export|list|print|show|return|give me|download)\b.{0,30}?"
            r"\b(all|every|entire|raw|full|whole)\b.{0,30}?"
            r"\b(records?|vectors?|embeddings?|chunks?|documents?|database|index"
            r"|knowledge base|metadata)\b"
            r"|\b(dump|export|list|print|show|return|give me|download|read|query)\b.{0,30}?"
            r"\b(your|the|this)\s+(pinecone|vector (store|database|db)|index|knowledge base)\b"
            r"|\braw\s+(chunks?|documents?|context|metadata|evidence|embeddings?)\b"
        ),
    ),
    (
        FABRICATION_REQUEST,
        re.compile(
            r"\bpretend\b|\b(make up|fabricate|exaggerate|embellish|inflate)\b"
            r"|\bassume (that )?(he|abhishek) (has|had|is|was|worked|built)\b"
            r"|^(please\s+)?(say|claim|state)\s+(that\s+)?(he|abhishek)\b"
        ),
    ),
    (
        SENSITIVE_PERSONAL_DATA,
        re.compile(
            r"\b(home|street|mailing|residential)\s+address\b|\bwhere does he live\b"
            r"|\b(date of birth|birthday|dob|how old)\b|\bssn\b|\bsocial security\b|\bpassport\b"
            r"|\bbank (account|details)\b|\bcredit card\b"
            r"|\b(personal|cell|mobile|home)\s+(phone|number)\b"
            r"|\bmarital\b|\breligio\w*\b|\b(medical|health)\s+(condition|history|records?)\b"
        ),
    ),
    (
        CONFIDENTIAL_EMPLOYER,
        re.compile(
            r"\b(confidential|proprietary|trade secrets?|non[- ]public|internal[- ]only)\b"
            r"|\b(client|customer)\s+(names?|lists?|data)\b|\bunder nda\b"
        ),
    ),
    (
        OUT_OF_SCOPE_TASK,
        re.compile(
            r"^(please\s+|can you\s+|could you\s+|help me\s+|now\s+)?"
            r"(write|generate|create|implement|debug|fix|refactor|solve|complete|build)\b.{0,40}?"
            r"\b(code|function|script|program|class|algorithm|sql|regex|website|app|essay|poem"
            r"|story|song|joke|cover letter|homework|assignment)\b"
            r"|^(please\s+)?translate\b"
            r"|\b(coding|programming|homework)\s+(assignment|task|problem|exercise)\b"
            r"|\bleetcode\b|\b(weather|stock price|horoscope|lottery|bitcoin price|recipe)\b"
            r"|\b(legal|medical|financial|tax|investment)\s+advice\b"
        ),
    ),
)

_UNSUPPORTED_CONTENT = re.compile(
    r"<\s*/?\s*[a-z][^>]*>|\b(javascript|vbscript)\s*:|\bdata:[a-z]+/|\bfile:/|```",
    re.IGNORECASE,
)
_ENCODED = re.compile(
    r"[A-Za-z0-9+/]{40,}={0,2}|\b(?:[0-9a-fA-F]{2}){20,}\b|(?:%[0-9a-fA-F]{2}){6,}"
    r"|(?:\\u[0-9a-fA-F]{4}){3,}|(?:\\x[0-9a-fA-F]{2}){4,}"
)


@dataclass(frozen=True)
class InputVerdict:
    allowed: bool
    category: str | None = None


def normalize_text(text: str) -> str:
    """Decode common obfuscations, then NFKC-normalize, casefold, and collapse whitespace."""
    decoded = html.unescape(unquote(text))
    decoded = _ZERO_WIDTH_RE.sub("", unicodedata.normalize("NFKC", decoded))
    return re.sub(r"\s+", " ", decoded).strip().casefold()


def contains_injection(text: str) -> bool:
    """Manipulation, extraction, or squashed-marker attack. Screens user input and evidence."""
    normalized = normalize_text(text)
    words = re.sub(r"[^a-z0-9]+", " ", normalized)
    squashed = re.sub(r"[^a-z]+", "", normalized.translate(_LEET))
    return (
        any(pattern.search(words) for pattern in INJECTION_PATTERNS)
        or any(pattern.search(words) for pattern in EXTRACTION_PATTERNS)
        or any(marker in squashed for marker in _SQUASHED_INJECTION)
    )


def check_input(message: str) -> InputVerdict:
    if _ENCODED.search(message):
        return InputVerdict(False, ENCODED_PAYLOAD)
    if _UNSUPPORTED_CONTENT.search(message) or _UNSUPPORTED_CONTENT.search(normalize_text(message)):
        return InputVerdict(False, UNSUPPORTED_CONTENT)
    if contains_injection(message):
        return InputVerdict(False, PROMPT_INJECTION)
    normalized = normalize_text(message)
    words = re.sub(r"[^a-z0-9.\s]+", " ", normalized)
    for category, pattern in _RULES:
        if pattern.search(normalized) or pattern.search(words):
            return InputVerdict(False, category)
    return InputVerdict(True)
