"""Compare two saved evaluation reports, e.g. the Phase 5 baseline and a candidate. No network.

    backend\\.venv\\Scripts\\python.exe -m evaluations.compare \\
        --baseline evaluations/reports/baseline-corrected --candidate evaluations/reports/candidate
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from evaluations.reporting import METRIC_ORDER


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    metrics = [
        {
            "metric": name,
            "baseline": baseline["metrics"].get(name),
            "candidate": candidate["metrics"].get(name),
            "delta": (
                round(candidate["metrics"][name] - baseline["metrics"][name], 4)
                if name in baseline["metrics"] and name in candidate["metrics"]
                else None
            ),
        }
        for name in METRIC_ORDER
        if name in baseline["metrics"] or name in candidate["metrics"]
    ]
    base_gates = {g["gate"]: g for g in baseline["gates"]}
    gates = [
        {
            "gate": g["gate"],
            "target": g["target"],
            "baseline": base_gates.get(g["gate"], {}).get("status"),
            "candidate": g["status"],
        }
        for g in candidate["gates"]
    ]
    base_failed = {f["case_id"] for f in baseline["failed_cases"]}
    cand_failed = {f["case_id"]: f for f in candidate["failed_cases"]}
    return {
        "baseline": baseline["run"]["label"],
        "candidate": candidate["run"]["label"],
        "metrics": metrics,
        "gates": gates,
        "all_gates_pass": candidate["all_gates_pass"],
        "fixed_cases": sorted(base_failed - set(cand_failed)),
        "still_failing": sorted(base_failed & set(cand_failed)),
        "new_failures": sorted(set(cand_failed) - base_failed),
        "candidate_failures": [
            {k: f[k] for k in ("case_id", "category", "root_cause", "issues")}
            for f in candidate["failed_cases"]
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    def fmt(value: Any) -> str:
        return "—" if value is None else f"{value:+.4f}" if isinstance(value, float) else str(value)

    lines = [
        f"# Evaluation comparison: `{result['baseline']}` vs `{result['candidate']}`",
        "",
        f"Candidate passes all gates: **{'yes' if result['all_gates_pass'] else 'no'}**",
        "",
        "| Metric | Baseline | Candidate | Delta |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {m['metric']} | {m['baseline']} | {m['candidate']} | {fmt(m['delta'])} |"
        for m in result["metrics"]
    ]
    lines += ["", "| Gate | Target | Baseline | Candidate |", "| --- | --- | --- | --- |"]
    lines += [
        f"| {g['gate']} | {g['target']} | {g['baseline']} | {str(g['candidate']).upper()} |"
        for g in result["gates"]
    ]
    lines += [
        "",
        f"Fixed: {', '.join(result['fixed_cases']) or 'none'}",
        f"Still failing: {', '.join(result['still_failing']) or 'none'}",
        f"New failures: {', '.join(result['new_failures']) or 'none'}",
        "",
    ]
    lines += [
        f"- `{f['case_id']}` ({f['category']}) {f['root_cause']}: {'; '.join(f['issues'])}"
        for f in result["candidate_failures"]
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evaluations.compare")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args(argv)
    baseline = json.loads((args.baseline / "report.json").read_text(encoding="utf-8"))
    candidate = json.loads((args.candidate / "report.json").read_text(encoding="utf-8"))
    result = compare(baseline, candidate)
    (args.candidate / "comparison.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(result)
    (args.candidate / "comparison.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
