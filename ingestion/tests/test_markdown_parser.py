from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.parsers.markdown import ParseError, parse_markdown_text
from ingestion.tests.conftest import document_text


def test_parses_front_matter_and_heading_paths() -> None:
    document = parse_markdown_text(document_text(), Path("doc.md"))

    assert document.raw_metadata["source_id"] == "resume-test"
    paths = [section.heading_path for section in document.sections]
    assert paths == [
        ("Jane Example", "SUMMARY"),
        (
            "Jane Example",
            "WORK EXPERIENCE",
            "Acme Corp, ML Engineer | 2020 - Present",
            "Fraud Platform",
        ),
        ("Jane Example", "SELECTED PROJECTS", "Demo Assistant"),
    ]
    fraud = document.sections[1]
    assert fraud.heading_levels == (1, 2, 3, 4)
    assert fraud.blocks == (
        "- Built a scoring platform ranking 45K claims.",
        "- Improved precision 23% -> 40% and F1 0.34 -> 0.52.",
    )
    assert document.headings_at_level(2) == {"SUMMARY", "WORK EXPERIENCE", "SELECTED PROJECTS"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("# No front matter\n", "missing YAML front matter"),
        ("---\nsource_id: x\n# never closed\n", "unterminated YAML front matter"),
        ("---\n- a list\n---\n", "front matter must be a YAML mapping"),
        ("---\nkey: [unclosed\n---\n", "invalid YAML front matter"),
    ],
)
def test_rejects_bad_front_matter(text: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_markdown_text(text, Path("doc.md"))


def test_ignores_headings_inside_code_fences() -> None:
    body = "## Real\n\n```\n# not a heading\n```\n"
    document = parse_markdown_text(document_text(body), Path("doc.md"))

    assert [s.heading_path for s in document.sections] == [("Real",)]
    assert document.sections[0].blocks == ("```\n# not a heading\n```",)


def test_nested_items_and_continuations_stay_with_parent_bullet() -> None:
    body = "## Skills\n\n- Parent item\n  continued line\n  - nested item\n- Second item\n"
    document = parse_markdown_text(document_text(body), Path("doc.md"))

    assert document.sections[0].blocks == (
        "- Parent item\n  continued line\n  - nested item",
        "- Second item",
    )


def test_handles_crlf_and_bom() -> None:
    text = "\ufeff" + document_text("## A\n\nText\n").replace("\n", "\r\n")
    document = parse_markdown_text(text, Path("doc.md"))

    assert document.sections[0].blocks == ("Text",)
