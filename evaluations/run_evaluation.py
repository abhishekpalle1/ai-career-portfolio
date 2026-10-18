"""Phase 5 evaluation CLI. Run from the repository root with the backend virtualenv:

    backend\\.venv\\Scripts\\python.exe -m evaluations.run_evaluation offline
    backend\\.venv\\Scripts\\python.exe -m evaluations.run_evaluation live --label candidate
    backend\\.venv\\Scripts\\python.exe -m evaluations.run_evaluation rescore \\
        --observations evaluations/reports/candidate/observations.jsonl --label candidate-rescored

`offline` and `rescore` make zero external calls. `live` requires ENABLE_LIVE_MODEL_CALLS=true and
ENABLE_LIVE_RAG=true and refuses the production Pinecone namespace. Existing report directories are
never overwritten without --overwrite.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from evaluations import REPO_ROOT
from evaluations.corpus import DEFAULT_MANIFEST, corpus_matches_manifest, load_corpus
from evaluations.dataset import DatasetError, load_dataset
from evaluations.evaluators.guardrails import prompt_fingerprints
from evaluations.observations import Observation, load_observations
from evaluations.reporting import build_report, cost_summary, sanitize, write_reports
from evaluations.scoring import evaluate_gates, score, score_separation

EVAL_DIR = REPO_ROOT / "evaluations"
DEFAULT_DATASET = EVAL_DIR / "datasets" / "golden.jsonl"
DEFAULT_THRESHOLDS = EVAL_DIR / "thresholds.yaml"
DEFAULT_REPORTS = EVAL_DIR / "reports"
DEFAULT_ENV_FILE = REPO_ROOT / "backend" / ".env"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evaluations.run_evaluation")
    parser.add_argument("mode", choices=["offline", "live", "rescore"])
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--label", default=None, help="Report folder under evaluations/reports/.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--observations", type=Path, default=None, help="rescore input file.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument(
        "--min-interval", type=float, default=4.0, help="Seconds between live cases."
    )
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N cases.")
    parser.add_argument("--cases", default=None, help="Comma-separated case IDs to evaluate.")
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace an existing report directory."
    )
    parser.add_argument("--skip-generation", action="store_true", help="Live retrieval only.")
    parser.add_argument("--no-fail", action="store_true", help="Exit 0 even if gates fail.")
    return parser


def _configuration(settings: Any | None) -> dict[str, Any]:
    from app.prompts.grounded_answer import PROMPT_VERSION

    if settings is None:
        return {"prompt_version": PROMPT_VERSION}
    return {
        "embedding_model": settings.gemini_embedding_model,
        "embedding_dimensions": settings.gemini_embedding_dimensions,
        "generation_model": settings.gemini_generation_model,
        "pinecone_index": settings.pinecone_index,
        "pinecone_namespace": settings.pinecone_namespace,
        "retrieval_top_k": settings.retrieval_top_k,
        "final_context_chunks": settings.final_context_chunks,
        "min_retrieval_score": settings.min_retrieval_score,
        "max_context_tokens": settings.max_context_tokens,
        "max_generation_retries": settings.max_generation_retries,
        "prompt_version": PROMPT_VERSION,
    }


def _display(path: Path) -> str:
    resolved = path.resolve()
    return (
        resolved.relative_to(REPO_ROOT).as_posix()
        if resolved.is_relative_to(REPO_ROOT)
        else resolved.as_posix()
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cases = load_dataset(args.dataset)
    except DatasetError as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2
    if args.limit:
        cases = cases[: args.limit]
    if args.cases:
        wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
        cases = [c for c in cases if c.case_id in wanted]
        missing = wanted - {c.case_id for c in cases}
        if missing:
            print(f"Unknown case IDs: {sorted(missing)}", file=sys.stderr)
            return 2
    config = yaml.safe_load(args.thresholds.read_text(encoding="utf-8"))
    corpus = load_corpus()
    unknown = sorted({cid for case in cases for cid in case.allowed_citation_ids} - set(corpus))
    if unknown:
        print(f"Dataset references chunk IDs missing from the corpus: {unknown}", file=sys.stderr)
        return 2

    label = args.label or args.mode
    output_dir = args.output_dir or DEFAULT_REPORTS / label
    # Recorded runs (such as the Phase 5 baseline) are immutable unless explicitly replaced.
    if (output_dir / "report.json").exists() and not args.overwrite:
        print(f"Refusing to overwrite {_display(output_dir)}; use a new --label.", file=sys.stderr)
        return 2
    settings = None
    stop_reason = None
    observations: list[Observation]

    if args.mode == "offline":
        from evaluations.runner import observe_offline

        observations = observe_offline(cases)
    elif args.mode == "rescore":
        source = args.observations or output_dir / "observations.jsonl"
        observations = load_observations(source)
    else:
        from app.core.config import Settings
        from evaluations.runner import observe_live

        settings = Settings(_env_file=args.env_file)
        if not settings.live_rag_enabled:
            print(
                "Live evaluation needs ENABLE_LIVE_MODEL_CALLS=true and ENABLE_LIVE_RAG=true.",
                file=sys.stderr,
            )
            return 2
        if settings.pinecone_namespace == "production":
            print("Refusing to evaluate against the production namespace.", file=sys.stderr)
            return 2
        observations, stop_reason = observe_live(
            cases,
            settings,
            min_interval_seconds=args.min_interval,
            skip_generation=args.skip_generation,
        )

    from app.prompts.grounded_answer import SYSTEM_PROMPT

    results, metrics = score(cases, observations, corpus, prompt_fingerprints(SYSTEM_PROMPT))
    mode = metrics["mode"]
    gates = evaluate_gates(metrics, config["gates"], mode)
    report = build_report(
        cases=cases,
        results=results,
        metrics=metrics,
        gates=gates,
        separation=score_separation(cases, observations),
        costs=cost_summary(observations, config),
        run_info={
            "label": label,
            "mode": args.mode,
            "dataset": _display(args.dataset),
            "cases": len(cases),
            "corpus_chunks": len(corpus),
            "corpus_matches_manifest": corpus_matches_manifest(corpus, DEFAULT_MANIFEST),
            "configuration": _configuration(settings),
            "stop_reason": stop_reason,
        },
    )
    paths = write_reports(output_dir, report, sanitize(observations, results))

    print(
        f"Mode: {mode} | cases evaluated: {metrics['cases_evaluated']} | "
        f"passed: {metrics['cases_passed']} | failed: {metrics['cases_failed']}"
    )
    for gate in gates:
        print(
            f"  {gate['status'].upper():<12} {gate['gate']:<34} {gate['target']:<8} "
            f"value={gate['value']}"
        )
    if stop_reason:
        print(f"Stopped early: {stop_reason}")
    print("Reports: " + ", ".join(_display(p) for p in paths))
    failed = any(g["status"] != "pass" for g in gates) or stop_reason is not None
    return 0 if args.no_fail or not failed else 1


if __name__ == "__main__":
    sys.exit(main())
