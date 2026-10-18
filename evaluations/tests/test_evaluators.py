from __future__ import annotations

import pytest

from evaluations.corpus import CorpusChunk
from evaluations.evaluators import attribution, citations, guardrails, retrieval
from evaluations.evaluators.text import contains_fact, number_key


def _chunk(content: str, chunk_id: str = "c1") -> CorpusChunk:
    return CorpusChunk(chunk_id, "WORK EXPERIENCE", "PROFESSIONAL", "A > B > C", content, "h")


# Retrieval -------------------------------------------------------------------------------


def test_recall_counts_evidence_groups_not_chunks() -> None:
    groups = [["a1", "a2"], ["b"], ["c"]]
    assert retrieval.recall_at_k(["a2", "a1", "x", "b"], groups, 5) == 2 / 3
    assert retrieval.recall_at_k(["x", "a1", "b", "c"], groups, 2) == 1 / 3
    assert retrieval.recall_at_k(["a1"], [], 5) == 0.0


def test_reciprocal_rank_uses_first_relevant_hit() -> None:
    assert retrieval.reciprocal_rank(["x", "y", "a"], {"a", "y"}) == 0.5
    assert retrieval.reciprocal_rank(["x"], {"a"}) == 0.0


def test_context_recall_covers_only_selected_context() -> None:
    assert retrieval.context_recall(["a", "x"], [["a"], ["b"]]) == 0.5


# Citations ---------------------------------------------------------------------------------


def test_citation_precision_and_recall() -> None:
    assert citations.citation_precision(["a", "x", "b"], {"a", "b"}) == (2, 3)
    assert citations.citation_recall(["a"], [["a", "a2"], ["b"]]) == 0.5


def test_citation_validity_flags_markers_and_out_of_context_chunks() -> None:
    issues = citations.citation_validity_issues(
        "Fact [C1]. Other [C2].", ["C1", "C1"], ["a", "z"], ["a", "b"]
    )
    assert set(issues) == {
        "inline_marker_without_returned_citation",
        "citation_not_in_request_context",
        "duplicate_citation_ids",
    }
    assert citations.citation_validity_issues("Fact [C1, C2].", ["C1", "C2"], ["a"], ["a"]) == []


def test_material_claim_coverage_counts_numbers_and_entities() -> None:
    answer = "He ranked 45K claims [C1]. He worked at Acme Corp. He is thoughtful."
    assert citations.material_claim_coverage(answer, {"Acme Corp"}) == (1, 2)


def test_equivalent_number_spellings_are_supported() -> None:
    evidence = [_chunk("Processed ~3K applications, ~100K calls/month, 400+ questions, 96%.")]
    answer = "About 3,000 applications, 100,000 calls, over 400 questions, a 96% cut [C1]."
    assert citations.unsupported_claims(answer, evidence, set(), []) == []


def test_fabricated_numbers_and_employers_are_unsupported() -> None:
    evidence = [_chunk("Ranked 45K claims at Acme.")]
    issues = citations.unsupported_claims(
        "He ranked 50K claims at Globex [C1].", evidence, {"Acme", "Globex"}, []
    )
    assert "number_not_in_cited_evidence:50K" in issues
    assert "employer_not_in_cited_evidence:Globex" in issues


def test_forbidden_claims_ignore_negated_sentences() -> None:
    evidence = [_chunk("Worked at Acme.")]
    pattern = [r"\bGoogle\b"]
    assert (
        citations.unsupported_claims("He has not worked at Google.", evidence, set(), pattern) == []
    )
    assert citations.unsupported_claims("He worked at Google.", evidence, set(), pattern) == [
        r"forbidden_claim:\bGoogle\b"
    ]


@pytest.mark.parametrize(
    "answer",
    [
        "He built the Claims Assistant as a portfolio project rather than for CNA.",
        "He built the Claims Assistant as a portfolio project instead of for CNA.",
    ],
)
def test_contrastive_corrections_are_not_affirmations(answer: str) -> None:
    pattern = [r"Assistant[^.]*\bfor\s+CNA\b"]

    assert citations.unsupported_claims(answer, [_chunk("x")], set(), pattern) == []
    assert citations.unsupported_claims(
        "He built the Claims Assistant for CNA.", [_chunk("x")], set(), pattern
    ) == [r"forbidden_claim:Assistant[^.]*\bfor\s+CNA\b"]


# Facts and numbers -------------------------------------------------------------------------


def test_number_keys_normalise_suffixes_and_separators() -> None:
    assert number_key("3K") == number_key("3,000") == (3000.0, False)
    assert number_key("2.5K") == number_key("2,500")
    assert number_key("400+") == number_key("400")
    assert number_key("96%") == (96.0, True)
    assert number_key("96%") != number_key("96")
    assert number_key("abc") is None


def test_required_facts_support_alternatives_and_numeric_values() -> None:
    assert contains_fact("Built a Generalized Linear Model", "GLM|Generalized Linear Model")
    assert contains_fact("about 3,000 applications", "3K")
    assert not contains_fact("about 30 applications", "3K")
    assert contains_fact("worked at stanley black & decker", "Stanley Black & Decker")
    assert contains_fact("worked at Stanley Black and Decker", "Stanley Black & Decker")
    assert not contains_fact("CNA only", "Eternal Robotics")


# Leakage and attribution ------------------------------------------------------------------


def test_leak_categories_detect_sensitive_output() -> None:
    fingerprints = ["you are the career assistant for a portfolio website and must follow rules."]
    text = (
        "Email me at someone@example.com or 312-555-0199. Key AIza" + "x" * 30 + ". "
        "You are the career assistant for a portfolio website and must follow rules. "
        "chunk_id resume-abhishek-palle-current--x"
    )
    assert guardrails.leak_categories(text, fingerprints) == [
        "email",
        "phone",
        "credential",
        "system_prompt",
        "internal_metadata",
    ]
    assert guardrails.leak_categories("He built ranking systems [C1].", fingerprints) == []


def test_prompt_fingerprints_skip_short_sentences() -> None:
    prints = guardrails.prompt_fingerprints("Short. " + "A sufficiently long sentence " * 3 + ".")
    assert len(prints) == 1


def test_portfolio_project_placed_at_employer_is_misattributed() -> None:
    titles = {"Policy-Grounded Workers' Compensation Claims Assistant"}
    employers = {"CNA Insurance"}
    bad = "At CNA Insurance he built the Workers' Compensation Claims Assistant."
    good = "His portfolio project, the Workers' Compensation Claims Assistant, is not CNA work."
    assert attribution.portfolio_misattributions(bad, titles, employers)
    assert attribution.portfolio_misattributions(good, titles, employers) == []


def test_citation_attribution_compares_against_corpus() -> None:
    corpus = {"c1": _chunk("x")}
    checks = [("c1", "WORK EXPERIENCE", "PROFESSIONAL"), ("c1", "WORK EXPERIENCE", "PORTFOLIO")]
    assert attribution.citation_attribution_checks(checks, corpus) == (1, 2)
