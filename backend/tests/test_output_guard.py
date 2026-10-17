"""Phase 4 output guardrails, using real résumé heading paths."""

import pytest

from app.guardrails.output_guard import REDACTION, check_output
from app.retrieval.vector_store import RetrievedChunk
from tests.rag_fakes import chunk

CNA = (
    "ABHISHEK PALLE > WORK EXPERIENCE > CNA Insurance, Senior Machine Learning Engineer "
    "| March 2021 - Present > Agentic LLM Platform for Underwriting Intelligence"
)
AUTO = "ABHISHEK PALLE > SELECTED PROJECTS > Agentic Commercial Auto Underwriting"
CONTEXT: list[RetrievedChunk] = [
    chunk("c-cna", 0.9, heading_path=CNA),
    chunk(
        "c-auto", 0.8, experience_type="PORTFOLIO", section="SELECTED PROJECTS", heading_path=AUTO
    ),
]


def verdict(text: str, max_characters: int = 1500) -> tuple[str, str | None]:
    result = check_output(text, CONTEXT, max_characters=max_characters)
    return result.verdict, result.reason


@pytest.mark.parametrize(
    "text",
    [
        "He processed ~3K business applications weekly at CNA Insurance [C1].",
        "Documented work includes:\n- An agentic LLM system [C1].\n- A portfolio project [C2].",
        "The approved materials do not document Google employment. They document CNA [C1].",
        "The materials document 8+ years building ML systems [C1]; they do not document 15.",
        "Agentic Commercial Auto Underwriting is a portfolio project [C2], not CNA work [C1].",
        "He not only shipped the platform but also built its eval harness [C1].",
    ],
)
def test_grounded_answers_pass(text: str) -> None:
    assert verdict(text) == ("PASS", None)


@pytest.mark.parametrize(
    "text",
    [
        "Abhishek has not worked at Google.",
        "He does not have Kubernetes experience.",
        "He never used AWS.",
        "No, he hasn't worked at Google.",
        "He has no experience with Kubernetes.",
    ],
)
def test_unsupported_negative_assertions_fail(text: str) -> None:
    assert verdict(text) == ("FAIL", "unsupported_negative_assertion")


def test_portfolio_project_placed_at_employer_fails() -> None:
    text = "He built the Agentic Commercial Auto Underwriting workflow at CNA Insurance [C2]."

    assert verdict(text) == ("FAIL", "portfolio_attributed_to_employer")
    assert verdict("He built the Commercial Auto workflow for CNA [C2].") == (
        "FAIL",
        "portfolio_attributed_to_employer",
    )


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("Key AIzaSyA1234567890abcdefghijklmnopqrstuv was used [C1].", "secret_in_output"),
        ("-----BEGIN RSA PRIVATE KEY----- [C1]", "secret_in_output"),
        ("The <retrieved_evidence> says he worked at CNA [C1].", "prompt_or_metadata_leak"),
        ("See [CHUNK C1] for details [C1].", "prompt_or_metadata_leak"),
        ("Its content_hash proves it [C1].", "prompt_or_metadata_leak"),
        ("See https://example.com for more [C1].", "url_or_html_in_output"),
        ("Click javascript:alert(1) [C1].", "url_or_html_in_output"),
        ("He built <b>systems</b> [C1].", "url_or_html_in_output"),
    ],
)
def test_leaks_urls_and_html_fail(text: str, reason: str) -> None:
    assert verdict(text) == ("FAIL", reason)


@pytest.mark.parametrize(
    ("text", "max_characters", "reason"),
    [
        ("He reduced forecast MAPE by 63%.", 1500, "uncited_fact"),
        ("His work includes:\n- An agentic LLM system", 1500, "uncited_bullet"),
        ("x" * 40 + " [C1].", 30, "answer_too_long"),
    ],
)
def test_repairable_formatting_failures(text: str, max_characters: int, reason: str) -> None:
    assert verdict(text, max_characters=max_characters) == ("REPAIRABLE", reason)


def test_emails_and_phone_numbers_are_redacted() -> None:
    result = check_output(
        "Contact someone@example.com or 555-010-0199 about CNA work [C1].",
        CONTEXT,
        max_characters=1500,
    )

    assert result.verdict == "PASS"
    assert "someone@example.com" not in result.answer
    assert "555-010-0199" not in result.answer
    assert result.answer.count(REDACTION) == 2


def test_metrics_with_at_sign_are_not_treated_as_email() -> None:
    result = check_output(
        "Achieved 0.78 mAP@0.5 on held-out data [C1].", CONTEXT, max_characters=1500
    )

    assert (result.verdict, result.answer) == (
        "PASS",
        "Achieved 0.78 mAP@0.5 on held-out data [C1].",
    )
