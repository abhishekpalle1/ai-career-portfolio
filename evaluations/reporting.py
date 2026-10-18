"""JSON and Markdown evaluation reports. Never includes secrets, prompts, or vectors."""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any

from evaluations.dataset import EvalCase
from evaluations.observations import Observation, save_observations
from evaluations.scoring import CaseResult

METRIC_ORDER = (
    "recall_at_5", "recall_at_10", "mrr", "context_recall", "citation_precision",
    "citation_recall", "citation_validity_rate", "material_claim_citation_coverage",
    "unsupported_claim_rate", "abstention_accuracy", "attribution_accuracy",
    "prompt_injection_block_rate", "system_prompt_extraction_rate",
    "sensitive_data_leakage_rate", "benign_pass_rate",
)  # fmt: skip


def sanitize(observations: list[Observation], results: list[CaseResult]) -> list[Observation]:
    leaked = {r.case_id: r.leaks for r in results if r.leaks}
    safe: list[Observation] = []
    for obs in observations:
        if obs.response is not None and obs.case_id in leaked:
            response = obs.response.model_copy(
                update={"answer": f"[withheld: leak detected ({', '.join(leaked[obs.case_id])})]"}
            )
            obs = obs.model_copy(update={"response": response})
        safe.append(obs)
    return safe


def cost_summary(observations: list[Observation], pricing: dict[str, Any]) -> dict[str, Any]:
    prices = pricing["pricing_usd_per_million_tokens"]
    embed_tokens = pricing["estimated_tokens_per_query_embedding"]
    totals = {
        "gemini_embedding_requests": sum(o.embed_requests for o in observations),
        "gemini_generation_requests": sum(o.generations for o in observations),
        "pinecone_queries": sum(o.pinecone_queries for o in observations),
        "pinecone_writes": 0,
        "generation_input_tokens": sum(o.input_tokens for o in observations),
        "generation_output_tokens": sum(o.output_tokens for o in observations),
        "generation_thinking_tokens": sum(o.thinking_tokens for o in observations),
    }
    cost = (
        totals["generation_input_tokens"] * prices["generation_input"]
        + (totals["generation_output_tokens"] + totals["generation_thinking_tokens"])
        * prices["generation_output"]
        + totals["gemini_embedding_requests"] * embed_tokens * prices["embedding_input"]
    ) / 1_000_000
    totals["estimated_cost_usd_at_paid_list_price"] = round(cost, 5)
    return totals


def build_report(
    *,
    cases: list[EvalCase],
    results: list[CaseResult],
    metrics: dict[str, Any],
    gates: list[dict[str, Any]],
    separation: dict[str, Any],
    costs: dict[str, Any],
    run_info: dict[str, Any],
) -> dict[str, Any]:
    by_case = {c.case_id: c for c in cases}
    categories: dict[str, Counter[str]] = {}
    for r in results:
        categories.setdefault(r.category, Counter())[r.status] += 1
    failed = [
        {
            "case_id": r.case_id,
            "category": r.category,
            "question": by_case[r.case_id].question,
            "expected_behavior": r.behavior,
            "root_cause": r.root_cause,
            "outcome": r.outcome,
            "issues": r.issues,
        }
        for r in results
        if r.status == "fail"
    ]
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "run": run_info,
        "metrics": {k: metrics[k] for k in METRIC_ORDER if k in metrics}
        | {k: metrics[k] for k in ("cases_evaluated", "cases_passed", "cases_failed", "mode")},
        "gates": gates,
        "all_gates_pass": all(g["status"] == "pass" for g in gates),
        "category_results": {k: dict(v) for k, v in sorted(categories.items())},
        "root_causes": dict(Counter(f["root_cause"] for f in failed).most_common()),
        "failed_cases": failed,
        "retrieval_score_separation": separation,
        "external_calls_and_cost": costs,
        "per_case": [
            {
                "case_id": r.case_id,
                "status": r.status,
                "recall_at_5": r.recall_at_5,
                "recall_at_10": r.recall_at_10,
                "reciprocal_rank": r.reciprocal_rank,
                "context_recall": r.context_recall,
                "citation_recall": r.citation_recall,
                "decision_correct": r.decision_correct,
                "outcome": r.outcome,
                "output_tokens": r.output_tokens,
                "claims": r.claims,
                "answer_words": r.answer_words,
                "issues": r.issues,
            }
            for r in results
        ],
    }


def _fmt(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def render_markdown(report: dict[str, Any]) -> str:
    run, costs = report["run"], report["external_calls_and_cost"]
    lines = [
        f"# RAG evaluation report — {run['label']}",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Mode: {report['metrics']['mode']}; dataset: `{run['dataset']}` ({run['cases']} cases)",
        f"- Corpus matches indexed manifest: {run['corpus_matches_manifest']}",
        f"- Configuration: `{json.dumps(run['configuration'])}`",
    ]
    if run.get("stop_reason"):
        lines.append(f"- **Run stopped early:** {run['stop_reason']}")
    lines += [
        f"- Cases: {report['metrics']['cases_evaluated']} evaluated, "
        f"{report['metrics']['cases_passed']} passed, {report['metrics']['cases_failed']} failed",
        "",
        "## Release gates",
        "",
        f"**All gates pass: {report['all_gates_pass']}**",
        "",
        "| Gate | Target | Value | Status | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {g['gate']} | {g['target']} | {_fmt(g['value'])} "
        f"| {g['status'].upper()} | {g['source']} |"
        for g in report["gates"]
    ]
    lines += ["", "## Metrics", "", "| Metric | Value |", "| --- | --- |"]
    lines += [f"| {k} | {_fmt(v)} |" for k, v in report["metrics"].items()]
    lines += ["", "## Results by category", "", "| Category | Pass | Fail | Not evaluated |"]
    lines += ["| --- | --- | --- | --- |"]
    lines += [
        f"| {cat} | {c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('not_evaluated', 0)} |"
        for cat, c in report["category_results"].items()
    ]
    lines += ["", "## Failure root causes", ""]
    lines += [f"- {cause}: {count}" for cause, count in report["root_causes"].items()] or ["None."]
    lines += ["", "## Failed cases", ""]
    for f in report["failed_cases"]:
        lines.append(
            f"- `{f['case_id']}` ({f['category']}, expected {f['expected_behavior']}) — "
            f"**{f['root_cause']}** — {f['question']}"
        )
        lines += [f"  - {issue}" for issue in f["issues"]]
    if not report["failed_cases"]:
        lines.append("None.")
    sep = report["retrieval_score_separation"]
    if sep:
        lines += ["", "## Retrieval score separation (MIN_RETRIEVAL_SCORE evidence)", ""]
        lines += [f"- {k}: {v}" for k, v in sep.items()]
    lines += ["", "## External calls and cost", ""]
    lines += [f"- {k}: {v}" for k, v in costs.items()]
    lines.append("")
    return "\n".join(lines)


def write_reports(
    output_dir: Path, report: dict[str, Any], observations: list[Observation]
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    md_path = output_dir / "report.md"
    obs_path = output_dir / "observations.jsonl"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    save_observations(obs_path, observations)
    return [json_path, md_path, obs_path]
