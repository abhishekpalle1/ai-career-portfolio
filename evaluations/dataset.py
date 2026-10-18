from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

Behavior = Literal["ANSWER", "DECLINE", "BLOCK", "SAFE", "OUT_OF_SCOPE", "REDIRECT"]

CATEGORIES = (
    "profile_summary",
    "professional_experience",
    "employer_history",
    "projects",
    "skills_technologies",
    "business_impact",
    "education",
    "multi_source",
    "unanswerable",
    "false_premise",
    "attribution",
    "prompt_injection",
    "prompt_extraction",
    "confidential_information",
    "citation_manipulation",
    "out_of_scope",
    "contact_redirect",
)
INJECTION_CATEGORIES = frozenset({"prompt_injection", "prompt_extraction"})
NON_BENIGN_CATEGORIES = INJECTION_CATEGORIES | {
    "confidential_information",
    "out_of_scope",
    "citation_manipulation",
}


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    category: str
    question: str
    expected_intent: str
    expected_behavior: Behavior
    relevant_chunk_ids: list[str]
    evidence_groups: list[list[str]]
    acceptable_chunk_ids: list[str]
    required_facts: list[str]
    forbidden_claims: list[str]
    expected_experience_type: Literal["PROFESSIONAL", "PORTFOLIO", "EDUCATION", "GENERAL"] | None
    notes: str = ""

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError(f"unknown category {value!r}")
        return value

    @field_validator("forbidden_claims")
    @classmethod
    def _valid_patterns(cls, value: list[str]) -> list[str]:
        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid forbidden_claims pattern {pattern!r}: {exc}") from exc
        return value

    @model_validator(mode="after")
    def _consistent(self) -> EvalCase:
        if self.expected_behavior == "ANSWER" and not self.relevant_chunk_ids:
            raise ValueError(f"{self.case_id}: ANSWER cases need relevant_chunk_ids")
        grouped = {cid for group in self.evidence_groups for cid in group}
        if not grouped <= set(self.relevant_chunk_ids):
            raise ValueError(f"{self.case_id}: evidence_groups must be within relevant_chunk_ids")
        return self

    @property
    def groups(self) -> list[list[str]]:
        """Evidence groups for recall; each relevant chunk is its own group by default."""
        return self.evidence_groups or [[cid] for cid in self.relevant_chunk_ids]

    @property
    def allowed_citation_ids(self) -> set[str]:
        return set(self.relevant_chunk_ids) | set(self.acceptable_chunk_ids)

    @property
    def benign(self) -> bool:
        return self.category not in NON_BENIGN_CATEGORIES


class DatasetError(ValueError):
    pass


def load_dataset(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(EvalCase.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise DatasetError(f"{path.name}:{number}: {exc}") from exc
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise DatasetError("duplicate case_id values")
    return cases
