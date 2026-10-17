from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ingestion.config import Settings
from ingestion.pipelines.ingest import INCLUDED, INVALID, RunResult


def document_totals(result: RunResult) -> dict[str, int]:
    return {
        "documents": len(result.documents),
        "included": sum(d.status == INCLUDED for d in result.documents),
        "skipped": sum(d.status not in (INCLUDED, INVALID) for d in result.documents),
        "invalid": sum(d.status == INVALID for d in result.documents),
    }


def build_report(result: RunResult, settings: Settings) -> dict[str, object]:
    plan = result.plan
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "mode": result.mode,
        "ok": result.ok,
        "live_services_used": result.mode == "apply",
        "settings": settings.public_summary(),
        "totals": {**document_totals(result), "chunks": len(result.chunks)},
        "documents": [
            {
                "path": d.path,
                "source_id": d.source_id,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "findings": [f.to_dict() for f in d.findings],
            }
            for d in result.documents
        ],
        "plan": None
        if plan is None
        else {
            "new": plan.new,
            "changed": plan.changed,
            "unchanged": plan.unchanged,
            "stale": plan.stale,
            "notes": plan.notes,
        },
        "actions": {
            "embedded": result.embedded,
            "upserted": result.upserted,
            "deleted": result.deleted,
        },
    }


def write_reports(result: RunResult, settings: Settings, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(result, settings)

    json_path = output_dir / "report.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown_path = output_dir / "report.md"
    markdown_path.write_text(_render_markdown(result, report), encoding="utf-8")

    chunks_path = output_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in result.chunks:
            record = {
                "id": chunk.chunk_id,
                "token_count": chunk.token_count,
                "metadata": chunk.record_metadata(),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return [json_path, markdown_path, chunks_path]


def _render_markdown(result: RunResult, report: dict[str, object]) -> str:
    lines = [
        "# Ingestion report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Mode: {result.mode}",
        f"- Status: {'OK' if result.ok else 'FAILED'}",
        f"- Settings: `{json.dumps(report['settings'])}`",
        "",
        "## Documents",
        "",
        "| Path | Source ID | Status | Chunks |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {d.path} | {d.source_id or '-'} | {d.status} | {d.chunk_count} |"
        for d in result.documents
    ]

    findings = [(d.path, f) for d in result.documents for f in d.findings]
    lines += ["", "## Findings", ""]
    lines += [
        f"- {f.severity} `{f.code}` {path}{f':{f.line}' if f.line else ''} - {f.message}"
        for path, f in findings
    ] or ["None."]

    if result.plan is not None:
        plan = result.plan
        lines += ["", "## Plan", ""]
        lines += [f"- Note: {note}" for note in plan.notes]
        for label, ids in (
            ("New", plan.new),
            ("Changed", plan.changed),
            ("Unchanged", plan.unchanged),
            ("Stale", plan.stale),
        ):
            lines.append(f"- {label}: {len(ids)}")
            lines += [f"  - `{chunk_id}`" for chunk_id in ids]

    lines += [
        "",
        "## Actions",
        "",
        f"- Embedded: {result.embedded}",
        f"- Upserted: {result.upserted}",
        f"- Deleted: {result.deleted}",
        "",
    ]
    return "\n".join(lines)


def format_summary(result: RunResult) -> str:
    lines = [f"Mode: {result.mode} | Status: {'OK' if result.ok else 'FAILED'}"]
    for document in result.documents:
        lines.append(f"  {document.status:<20} {document.path} ({document.chunk_count} chunks)")
        for finding in document.findings:
            where = f" line {finding.line}" if finding.line else ""
            lines.append(f"    {finding.severity} {finding.code}{where}: {finding.message}")
    totals = document_totals(result)
    lines.append(
        f"Documents: {totals['included']} included, {totals['skipped']} skipped, "
        f"{totals['invalid']} rejected (invalid)"
    )
    if result.plan is not None:
        plan = result.plan
        lines.append(
            f"Plan: {len(plan.new)} new, {len(plan.changed)} changed, "
            f"{len(plan.unchanged)} unchanged, {len(plan.stale)} stale"
        )
        lines += [f"  Note: {note}" for note in plan.notes]
    if result.mode in ("apply", "offline-persist"):
        lines.append(
            f"Actions: {result.embedded} embedded, {result.upserted} upserted, "
            f"{result.deleted} deleted"
        )
    return "\n".join(lines)
