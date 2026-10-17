from __future__ import annotations

import re
from pathlib import Path

import yaml

from ingestion.models import ParsedDocument, Section

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
# Only top-level items start a new block, so nested items stay with their parent.
_LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")


class ParseError(ValueError):
    pass


def parse_markdown(path: Path) -> ParsedDocument:
    return parse_markdown_text(path.read_text(encoding="utf-8"), path)


def parse_markdown_text(text: str, path: Path) -> ParsedDocument:
    lines = text.lstrip("\ufeff").replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ParseError("missing YAML front matter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ParseError("unterminated YAML front matter")

    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" near line {mark.line + 2}" if mark is not None else ""
        raise ParseError(f"invalid YAML front matter{where}") from None
    if not isinstance(data, dict):
        raise ParseError("front matter must be a YAML mapping")

    sections = _split_sections(lines[end + 1 :], first_line_number=end + 2)
    return ParsedDocument(
        path=path,
        raw_metadata={str(key): value for key, value in data.items()},
        sections=tuple(sections),
    )


def _split_sections(lines: list[str], first_line_number: int) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    current: list[str] = []
    current_line = first_line_number
    in_fence = False

    def close() -> None:
        blocks = _split_blocks(current)
        if blocks:
            sections.append(
                Section(
                    heading_path=tuple(title for _, title in stack),
                    heading_levels=tuple(level for level, _ in stack),
                    blocks=tuple(blocks),
                    line=current_line,
                )
            )

    for offset, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING_RE.match(line)
        if heading is None:
            current.append(line)
            continue
        close()
        level, title = len(heading.group(1)), heading.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        current = []
        current_line = first_line_number + offset
    close()
    return sections


def _split_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False

    def flush() -> None:
        text = "\n".join(current).strip()
        if text:
            blocks.append(text)
        current.clear()

    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            current.append(line.rstrip())
            continue
        if in_fence:
            current.append(line.rstrip())
            continue
        if not line.strip():
            flush()
            continue
        if _LIST_ITEM_RE.match(line):
            flush()
        current.append(line.rstrip())
    flush()
    return blocks


def is_list_item(block: str) -> bool:
    return bool(_LIST_ITEM_RE.match(block))
