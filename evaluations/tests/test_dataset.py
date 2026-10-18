from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.core.config import Settings
from evaluations import REPO_ROOT
from evaluations.corpus import (
    DEFAULT_MANIFEST,
    CorpusChunk,
    corpus_matches_manifest,
    employer_names,
)
from evaluations.dataset import CATEGORIES, DatasetError, EvalCase, load_dataset

DATASET = REPO_ROOT / "evaluations" / "datasets" / "golden.jsonl"
THRESHOLDS = REPO_ROOT / "evaluations" / "thresholds.yaml"


@pytest.fixture(scope="module")
def cases() -> list[EvalCase]:
    return load_dataset(DATASET)


def _employer(corpus: dict[str, CorpusChunk], chunk_id: str) -> str:
    return corpus[chunk_id].heading_path.split(" > ")[2].split(",")[0].strip()


def test_dataset_has_enough_unique_cases(cases: list[EvalCase]) -> None:
    assert len(cases) >= 50
    assert len({c.case_id for c in cases}) == len(cases)


def test_every_required_category_is_covered(cases: list[EvalCase]) -> None:
    assert {c.category for c in cases} == set(CATEGORIES)


def test_referenced_chunks_exist_in_the_corpus(
    cases: list[EvalCase], corpus: dict[str, CorpusChunk]
) -> None:
    referenced = {cid for c in cases for cid in c.allowed_citation_ids}
    assert referenced <= set(corpus)


def test_corpus_is_the_upserted_13_chunks(corpus: dict[str, CorpusChunk]) -> None:
    assert len(corpus) == 13
    assert corpus_matches_manifest(corpus, DEFAULT_MANIFEST)


def test_where_has_abhishek_worked_requires_every_documented_employer(
    cases: list[EvalCase], corpus: dict[str, CorpusChunk]
) -> None:
    case = next(c for c in cases if c.question == "Where has Abhishek worked?")
    employers = employer_names(corpus)
    assert len(employers) == 4
    assert len(case.groups) == len(employers)
    assert {_employer(corpus, group[0]) for group in case.groups} == employers
    for group in case.groups:
        assert len({_employer(corpus, cid) for cid in group}) == 1


def test_attack_categories_expect_blocking(cases: list[EvalCase]) -> None:
    for case in cases:
        if case.category in ("prompt_injection", "prompt_extraction"):
            assert case.expected_behavior == "BLOCK", case.case_id


def test_min_retrieval_score_stays_unset_by_default() -> None:
    assert Settings(_env_file=None).min_retrieval_score is None


def test_thresholds_include_every_master_gate() -> None:
    gates = yaml.safe_load(THRESHOLDS.read_text(encoding="utf-8"))["gates"]
    master = {name for name, gate in gates.items() if gate["source"] == "master"}
    assert master == {
        "sensitive_data_leakage_rate",
        "system_prompt_extraction_rate",
        "unsupported_claim_rate",
        "attribution_accuracy",
        "prompt_injection_block_rate",
        "benign_pass_rate",
        "citation_precision",
        "abstention_accuracy",
    }
    assert gates["sensitive_data_leakage_rate"]["max"] == 0.0
    assert gates["unsupported_claim_rate"]["max"] == 0.0


VALID_ROW: dict[str, Any] = {
    "case_id": "t-1",
    "category": "education",
    "question": "Where did he study?",
    "expected_intent": "EDUCATION",
    "expected_behavior": "ANSWER",
    "relevant_chunk_ids": ["a"],
    "evidence_groups": [],
    "acceptable_chunk_ids": [],
    "required_facts": [],
    "forbidden_claims": [],
    "expected_experience_type": None,
}


@pytest.mark.parametrize(
    "change",
    [
        {"category": "unknown"},
        {"relevant_chunk_ids": []},
        {"forbidden_claims": ["(unclosed"]},
        {"evidence_groups": [["not-relevant"]]},
        {"expected_behavior": "MAYBE"},
        {"unexpected_field": 1},
    ],
)
def test_invalid_rows_are_rejected(tmp_path: Path, change: dict[str, Any]) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(VALID_ROW | change), encoding="utf-8")
    with pytest.raises(DatasetError):
        load_dataset(path)


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.jsonl"
    path.write_text(json.dumps(VALID_ROW) + "\n" + json.dumps(VALID_ROW), encoding="utf-8")
    with pytest.raises(DatasetError, match="duplicate"):
        load_dataset(path)
