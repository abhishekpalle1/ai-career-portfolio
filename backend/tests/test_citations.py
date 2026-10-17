"""Inline citation markers: single, grouped, duplicate, unknown, and malformed."""

import re

import pytest

from app.services.generation import GeneratedClaim
from app.services.rag_assistant import ABSTENTION_ANSWER, RagAssistant, parse_inline_citations
from tests.rag_fakes import FakeEmbedder, FakeGenerator, FakeRetriever, answer, chunk, live_settings


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Built X [C1].", ["C1"]),
        ("Built X [C1, C3].", ["C1", "C3"]),
        ("Built X [C1,C3].", ["C1", "C3"]),
        ("Built X [C1, C2, C4].", ["C1", "C2", "C4"]),
        ("Built X [ C2 ,C1 ].", ["C2", "C1"]),
        ("A [C1]. B [C3][C2].", ["C1", "C3", "C2"]),
    ],
)
def test_parses_single_and_grouped_markers(text: str, expected: list[str]) -> None:
    assert parse_inline_citations(text) == (expected, False)


def test_duplicate_ids_are_extracted_once() -> None:
    assert parse_inline_citations("A [C1]. B [C1, C1]. C [C2, C1].") == (["C1", "C2"], False)


def test_brackets_without_citation_tokens_are_ignored() -> None:
    assert parse_inline_citations("He wrote [sic] and used [Python].") == ([], False)


@pytest.mark.parametrize(
    "marker",
    ["[C1 C3]", "[C1;C3]", "[C1,]", "[,C1]", "[C1,,C3]", "[C1, see C3]", "[c1]", "[C1-C3]",
     "[C 1]", "[C1, C 3]", "[Ref C1]"],
)  # fmt: skip
def test_malformed_grouped_markers_are_flagged(marker: str) -> None:
    assert parse_inline_citations(f"Claim {marker}.")[1] is True


def _assistant(text: str, claim_ids: list[str], citation_ids: list[str]) -> RagAssistant:
    context = [
        chunk("c-cna", 0.9),
        chunk("c-summary", 0.8, experience_type="GENERAL", section="SUMMARY"),
        chunk("c-skills", 0.7, experience_type="GENERAL", section="TECHNICAL SKILLS"),
        chunk("c-sbd", 0.6),
    ]
    claims = [
        GeneratedClaim(
            text="claim",
            citation_ids=claim_ids,
            support_level="SUPPORTED",
            experience_type="GENERAL",
        )
    ]
    result = answer(text, claims=claims, citation_ids=citation_ids)
    return RagAssistant(
        live_settings(), FakeEmbedder(), FakeRetriever(context), FakeGenerator(result)
    )


def test_grouped_marker_ids_are_all_returned_as_citations() -> None:
    # Live regression: "[C1, C3]" appeared in text while claims listed only C1.
    response = _assistant("Built on Google Cloud [C1, C3].", ["C1"], ["C1"]).answer(
        "Has he worked at Google?"
    )

    assert response.grounded is True
    assert [(c.citation_id, c.chunk_id) for c in response.citations] == [
        ("C1", "c-cna"),
        ("C3", "c-skills"),
    ]


@pytest.mark.parametrize("text", ["X [C1,C2, C4].", "X [C1][C2] and [C4, C2]."])
def test_every_inline_marker_has_a_returned_citation(text: str) -> None:
    response = _assistant(text, ["C1"], ["C1"]).answer("What has he built?")

    returned = {c.citation_id for c in response.citations}
    inline = set(re.findall(r"C\d+", text))
    assert inline <= returned
    assert returned == {"C1", "C2", "C4"}


@pytest.mark.parametrize(
    "text", ["X [C1, C9].", "X [C5].", "X [C0]."], ids=["grouped", "single", "zero"]
)
def test_unknown_ids_abstain(text: str) -> None:
    response = _assistant(text, ["C1"], ["C1"]).answer("What has he built?")

    assert response.abstained is True
    assert response.answer == ABSTENTION_ANSWER
    assert response.citations == []


@pytest.mark.parametrize("text", ["X [C1 C3].", "X [C1;C2].", "X [C1,]."])
def test_malformed_markers_abstain(text: str) -> None:
    response = _assistant(text, ["C1"], ["C1"]).answer("What has he built?")

    assert response.abstained is True
    assert response.citations == []


def test_non_retrieved_ids_in_citation_list_still_abstain() -> None:
    response = _assistant("X [C1].", ["C1"], ["C1", "C7"]).answer("What has he built?")

    assert response.abstained is True
