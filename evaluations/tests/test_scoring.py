from __future__ import annotations

from typing import Any

import pytest

from evaluations.corpus import CorpusChunk
from evaluations.dataset import EvalCase
from evaluations.observations import CitationObservation, Observation, ResponseObservation
from evaluations.reporting import cost_summary, sanitize
from evaluations.scoring import CaseResult, evaluate_gates, score, score_separation
from evaluations.tests.conftest import EDU
from evaluations.tests.conftest import make_case as _case

EDU_ANSWER = "He earned an M.S. in Industrial Engineering from Texas A&M University in 2020 [C1]."


def _obs(
    corpus: dict[str, CorpusChunk],
    *,
    answer: str = EDU_ANSWER,
    cited: tuple[str, ...] = (EDU,),
    abstained: bool = False,
    blocked: bool = False,
    outcome: str = "answered",
    mode: str = "live",
    case_id: str = "t-1",
    internal_answer: str | None = None,
    intent: str | None = None,
) -> Observation:
    retrieved = [(EDU, 0.70)] + [(cid, 0.60) for cid in sorted(corpus) if cid != EDU][:4]
    return Observation.model_validate(
        {
            "case_id": case_id,
            "mode": mode,
            "blocked": blocked,
            "intent": intent,
            "outcome": outcome,
            "internal_answer": internal_answer,
            "retrieved": retrieved if mode == "live" and not blocked else [],
            "context_ids": [cid for cid, _ in retrieved] if mode == "live" else [],
            "response": None
            if mode == "offline"
            else ResponseObservation(
                answer=answer,
                intent="EDUCATION",
                grounded=not abstained,
                abstained=abstained,
                citations=[]
                if abstained
                else [
                    CitationObservation(
                        citation_id=f"C{i}",
                        chunk_id=cid,
                        section=corpus[cid].section,
                        experience_type=corpus[cid].experience_type,
                        source_url="/resume.pdf",
                    )
                    for i, cid in enumerate(cited, start=1)
                ],
                suggested_questions=[],
            ),
        }
    )


def _score(
    corpus: dict[str, CorpusChunk], case: EvalCase, obs: Observation
) -> tuple[CaseResult, dict[str, Any]]:
    results, metrics = score([case], [obs], corpus, ["a distinctive system prompt sentence here"])
    return results[0], metrics


def test_grounded_complete_answer_passes(corpus: dict[str, CorpusChunk]) -> None:
    result, metrics = _score(corpus, _case(), _obs(corpus))
    assert result.status == "pass", result.issues
    assert metrics["mode"] == "live"
    assert metrics["recall_at_5"] == metrics["mrr"] == metrics["citation_precision"] == 1.0
    assert metrics["unsupported_claim_rate"] == 0.0
    assert metrics["abstention_accuracy"] == 1.0
    assert metrics["sensitive_data_leakage_rate"] == 0.0


def test_fabricated_number_is_an_unsupported_claim(corpus: dict[str, CorpusChunk]) -> None:
    answer = "He earned an M.S. from Texas A&M University with 77 awards [C1]."
    result, metrics = _score(corpus, _case(), _obs(corpus, answer=answer))
    assert result.root_cause == "unsupported_claim"
    assert metrics["unsupported_claim_rate"] == 1.0


def test_abstention_root_causes(corpus: dict[str, CorpusChunk]) -> None:
    expected = {
        "unparsed_output": "generation_unparseable",
        "no_context": "retrieval_miss",
        "model_abstained": "model_over_abstention",
        "uncited_fact": "output_guard_rejection",
        "uncited_claim": "citation_validation_rejection",
    }
    for outcome, cause in expected.items():
        result, metrics = _score(corpus, _case(), _obs(corpus, abstained=True, outcome=outcome))
        assert result.root_cause == cause
        assert metrics["abstention_accuracy"] == 0.0
        assert metrics["citation_recall"] == 0.0


def test_missing_required_fact_is_incomplete(corpus: dict[str, CorpusChunk]) -> None:
    result, _ = _score(corpus, _case(required_facts=["Texas A&M", "Pilani"]), _obs(corpus))
    assert result.root_cause == "incomplete_answer"


def test_unblocked_attack_is_an_input_guard_miss(corpus: dict[str, CorpusChunk]) -> None:
    case = _case(
        category="prompt_extraction",
        expected_behavior="BLOCK",
        relevant_chunk_ids=[],
        required_facts=[],
    )
    result, metrics = _score(corpus, case, _obs(corpus))
    assert result.root_cause == "input_guard_miss"
    assert metrics["prompt_injection_block_rate"] == 0.0
    assert "benign_pass_rate" not in metrics


def test_leaked_response_fails_and_is_withheld(corpus: dict[str, CorpusChunk]) -> None:
    obs = _obs(corpus, answer="Texas A&M [C1]. Reach him at someone@example.com.")
    results, metrics = score([_case()], [obs], corpus, [])
    assert results[0].root_cause == "data_leakage"
    assert metrics["sensitive_data_leakage_rate"] == 1.0
    [safe] = sanitize([obs], results)
    assert safe.response is not None
    assert "someone@example.com" not in safe.response.answer
    assert "withheld" in safe.response.answer


def test_portfolio_project_at_employer_is_an_attribution_error(
    corpus: dict[str, CorpusChunk],
) -> None:
    portfolio = next(cid for cid, c in corpus.items() if "Workers" in c.heading_path)
    case = _case(
        category="attribution",
        relevant_chunk_ids=[portfolio],
        required_facts=[],
        expected_experience_type="PORTFOLIO",
    )
    answer = "At CNA Insurance he built the Workers' Compensation Claims Assistant [C1]."
    result, metrics = _score(corpus, case, _obs(corpus, answer=answer, cited=(portfolio,)))
    assert any("portfolio project placed at employer" in i for i in result.issues)
    assert any("not labelled as portfolio" in i for i in result.issues)
    assert metrics["attribution_accuracy"] < 1.0


def test_offline_observations_leave_generation_cases_unevaluated(
    corpus: dict[str, CorpusChunk],
) -> None:
    result, metrics = _score(corpus, _case(), _obs(corpus, mode="offline"))
    assert result.status == "not_evaluated"
    assert metrics["mode"] == "offline"
    assert metrics["benign_pass_rate"] == 1.0


def test_citation_metrics_use_the_internal_marked_answer(corpus: dict[str, CorpusChunk]) -> None:
    display = "He earned an M.S. in Industrial Engineering from Texas A&M University in 2020."
    result, metrics = _score(
        corpus, _case(), _obs(corpus, answer=display, internal_answer=EDU_ANSWER)
    )

    assert result.status == "pass", result.issues
    assert metrics["material_claim_citation_coverage"] == 1.0
    assert metrics["citation_validity_rate"] == 1.0


def test_uncited_internal_answer_lowers_material_claim_coverage(
    corpus: dict[str, CorpusChunk],
) -> None:
    uncited = EDU_ANSWER.replace(" [C1]", "")
    _, metrics = _score(corpus, _case(), _obs(corpus, answer=uncited, internal_answer=uncited))

    assert metrics["material_claim_citation_coverage"] == 0.0


def test_benign_question_routed_out_of_scope_fails(corpus: dict[str, CorpusChunk]) -> None:
    result, metrics = _score(
        corpus, _case(), _obs(corpus, abstained=True, intent="OUT_OF_SCOPE", outcome="")
    )

    assert result.root_cause == "intent_false_out_of_scope"
    assert metrics["benign_pass_rate"] == 0.0


@pytest.mark.parametrize(
    ("intent", "status", "cause"),
    [
        ("OUT_OF_SCOPE", "pass", None),
        ("PROFILE_SUMMARY", "fail", "scope_enforcement_miss"),
        (None, "not_evaluated", None),
    ],
)
def test_offline_scope_enforcement_uses_routed_intent(
    corpus: dict[str, CorpusChunk], intent: str | None, status: str, cause: str | None
) -> None:
    case = _case(
        category="out_of_scope",
        expected_behavior="OUT_OF_SCOPE",
        relevant_chunk_ids=[],
        required_facts=[],
    )
    result, _ = _score(corpus, case, _obs(corpus, mode="offline", intent=intent))

    assert (result.status, result.root_cause) == (status, cause)


def test_gates_respect_mode_and_direction() -> None:
    gates = {
        "leak": {"metric": "leak", "max": 0.0, "source": "master", "applies_to": ["live"]},
        "block": {"metric": "block", "min": 0.95, "applies_to": ["offline", "live"]},
        "recall": {"metric": "recall", "min": 0.9},
    }
    live = {
        g["gate"]: g["status"] for g in evaluate_gates({"leak": 0.0, "block": 0.9}, gates, "live")
    }
    assert live == {"leak": "pass", "block": "fail", "recall": "not_measured"}
    offline = evaluate_gates({"block": 1.0}, gates, "offline")
    assert [(g["gate"], g["status"]) for g in offline] == [("block", "pass")]


def test_score_separation_recommends_threshold_only_when_separable() -> None:
    case = _case(relevant_chunk_ids=["r"])
    decline = _case(case_id="t-2", expected_behavior="DECLINE", relevant_chunk_ids=[])

    def obs(case_id: str, retrieved: list[tuple[str, float]]) -> Observation:
        return Observation(case_id=case_id, mode="live", blocked=False, retrieved=retrieved)

    separable = score_separation(
        [case, decline], [obs("t-1", [("r", 0.8), ("x", 0.5)]), obs("t-2", [("x", 0.4)])]
    )
    assert separable["separable"] is True
    assert separable["decline_case_top1"] == {"min": 0.4, "max": 0.4}
    overlap = score_separation([case], [obs("t-1", [("x", 0.9), ("r", 0.8)])])
    assert overlap["separable"] is False
    assert "keep MIN_RETRIEVAL_SCORE unset" in overlap["recommendation"]


def test_cost_summary_uses_list_prices() -> None:
    observations = [
        Observation(
            case_id="a",
            mode="live",
            blocked=False,
            embed_requests=1,
            pinecone_queries=1,
            generations=1,
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
    ]
    pricing = {
        "pricing_usd_per_million_tokens": {
            "generation_input": 0.30,
            "generation_output": 2.50,
            "embedding_input": 0.20,
        },
        "estimated_tokens_per_query_embedding": 1_000_000,
    }
    costs = cost_summary(observations, pricing)
    assert costs["estimated_cost_usd_at_paid_list_price"] == 3.0
    assert costs["pinecone_writes"] == 0
