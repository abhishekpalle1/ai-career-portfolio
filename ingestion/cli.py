"""Offline ingestion CLI. Run from the repository root: python -m ingestion.cli --help"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from ingestion.config import (
    DEFAULT_KB_DIR,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_OUTPUT_DIR,
    ConfigError,
    Settings,
    load_env_file,
)
from ingestion.pipelines.ingest import IngestionError, run_ingestion, validate_corpus
from ingestion.pipelines.manifest import ManifestError
from ingestion.pipelines.report import format_summary, write_reports


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingestion.cli",
        description="Validate, chunk, and index the approved knowledge base.",
    )
    parser.add_argument("--kb-dir", type=Path, default=DEFAULT_KB_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Read settings from a KEY=VALUE file (for example backend/.env). "
        "Process environment variables take precedence. Values are never printed.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="Validate metadata, sensitive content, and chunking only.")
    commands.add_parser(
        "preflight",
        help="No-network, no-write check that --apply is configured and the corpus is valid.",
    )

    ingest = commands.add_parser(
        "ingest", help="Plan an ingestion run. Dry run unless --apply is given."
    )
    mode = ingest.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Embed with Gemini and upsert to Pinecone (requires ENABLE_LIVE_MODEL_CALLS=true "
        "and ENABLE_LIVE_VECTOR_UPSERTS=true).",
    )
    mode.add_argument(
        "--persist-manifest",
        action="store_true",
        help="Offline: write the plan to a non-production --manifest with no embedding or "
        "vector-store calls, to verify change detection.",
    )
    ingest.add_argument(
        "--delete-stale",
        action="store_true",
        help="Delete vectors whose chunks no longer exist in the knowledge base.",
    )
    return parser


def sanitized_error(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    if status is None and isinstance(code, int):
        # google-genai: `code` is the HTTP status and `status` the provider status name.
        status, code = code, getattr(exc, "status", None)
    if status is None and isinstance(getattr(exc, "status", None), int):
        status = getattr(exc, "status", None)
    safe_code = code if isinstance(code, str) and code.replace("_", "").isalnum() else None
    return f"{type(exc).__name__} http_status={status} provider_code={safe_code}"


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        env = dict(os.environ)
        if args.env_file is not None:
            env = {**load_env_file(args.env_file), **env}
        settings = Settings.from_env(env)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.command == "validate":
        result = validate_corpus(args.kb_dir, settings)
        print(format_summary(result))
        return 0 if result.ok else 1

    if args.command == "preflight":
        from ingestion.preflight import block_network, run_preflight

        with block_network() as attempts:
            lines, problems = run_preflight(args.kb_dir, args.manifest, settings, args.env_file)
        print("Ingestion apply preflight (no network, no writes)")
        for line in lines:
            print(f"  {line}")
        print(f"  Network attempts blocked: {len(attempts)}")
        for problem in problems:
            print(f"  PROBLEM: {problem}")
        print(
            "Result: " + ("READY (live flags still gate --apply)" if not problems else "NOT READY")
        )
        return 0 if not problems else 1

    if args.persist_manifest and args.manifest.resolve() == DEFAULT_MANIFEST_PATH.resolve():
        print(
            "--persist-manifest requires --manifest pointing away from the production manifest",
            file=sys.stderr,
        )
        return 2

    embedder = store = None
    if args.apply:
        missing = settings.missing_live_requirements()
        if missing:
            print(f"Apply refused. Missing: {', '.join(missing)}", file=sys.stderr)
            return 2
        print(f"Target: index={settings.pinecone_index} namespace={settings.pinecone_namespace}")

    try:
        if args.apply:
            from ingestion.adapters.gemini_embedder import GeminiEmbedder
            from ingestion.adapters.pinecone_store import PineconeVectorStore

            embedder = GeminiEmbedder.from_settings(settings)
            store = PineconeVectorStore.from_settings(settings)
        result = run_ingestion(
            args.kb_dir,
            settings,
            manifest_path=args.manifest,
            apply=args.apply,
            persist_manifest=args.persist_manifest,
            delete_stale=args.delete_stale,
            embedder=embedder,
            store=store,
        )
    except (IngestionError, ManifestError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if not args.apply:
            raise
        # Provider messages can echo request details, so report only safe identifiers.
        print(f"Live dependency failed: {sanitized_error(exc)}", file=sys.stderr)
        print("No manifest update. Re-run preflight to confirm the plan.", file=sys.stderr)
        return 1

    paths = write_reports(result, settings, args.output_dir)
    print(format_summary(result))
    print("Reports: " + ", ".join(str(path) for path in paths))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
