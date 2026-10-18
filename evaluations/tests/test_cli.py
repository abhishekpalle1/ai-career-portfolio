from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.prompts.grounded_answer import SYSTEM_PROMPT
from evaluations.compare import main as compare_main
from evaluations.evaluators.guardrails import prompt_fingerprints
from evaluations.run_evaluation import DEFAULT_DATASET, main


def _report(directory: Path) -> dict[str, object]:
    report: dict[str, object] = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    return report


def test_offline_mode_writes_reports_with_zero_external_calls(
    tmp_path: Path, blocked_network: list[str]
) -> None:
    assert main(["offline", "--output-dir", str(tmp_path), "--no-fail"]) == 0
    assert {p.name for p in tmp_path.iterdir()} == {
        "report.json",
        "report.md",
        "observations.jsonl",
    }
    report = _report(tmp_path)
    costs = report["external_calls_and_cost"]
    assert isinstance(costs, dict)
    assert costs["estimated_cost_usd_at_paid_list_price"] == 0
    assert costs["gemini_generation_requests"] == costs["pinecone_queries"] == 0
    assert blocked_network == []


def test_offline_exit_code_reflects_release_gates(tmp_path: Path) -> None:
    code = main(["offline", "--output-dir", str(tmp_path)])
    assert code == (0 if _report(tmp_path)["all_gates_pass"] else 1)


def test_rescore_reproduces_metrics_from_saved_observations(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    main(["offline", "--output-dir", str(first), "--no-fail"])
    observations = first / "observations.jsonl"
    assert (
        main(
            [
                "rescore",
                "--observations",
                str(observations),
                "--output-dir",
                str(second),
                "--no-fail",
            ]
        )
        == 0
    )
    assert _report(first)["metrics"] == _report(second)["metrics"]


def test_reports_do_not_contain_the_system_prompt(tmp_path: Path) -> None:
    main(["offline", "--output-dir", str(tmp_path), "--no-fail"])
    text = " ".join(p.read_text(encoding="utf-8").casefold() for p in tmp_path.iterdir())
    assert not any(fp in text for fp in prompt_fingerprints(SYSTEM_PROMPT))


def test_live_mode_requires_live_flags(tmp_path: Path, blocked_network: list[str]) -> None:
    env = tmp_path / "empty.env"
    env.write_text("", encoding="utf-8")
    assert main(["live", "--env-file", str(env), "--output-dir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()
    assert blocked_network == []


def test_live_mode_refuses_the_production_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocked_network: list[str]
) -> None:
    env = tmp_path / "empty.env"
    env.write_text("", encoding="utf-8")
    monkeypatch.setenv("ENABLE_LIVE_MODEL_CALLS", "true")
    monkeypatch.setenv("ENABLE_LIVE_RAG", "true")
    monkeypatch.setenv("PINECONE_NAMESPACE", "production")
    assert main(["live", "--env-file", str(env), "--output-dir", str(tmp_path / "out")]) == 2
    assert blocked_network == []


def test_existing_reports_are_never_overwritten(tmp_path: Path) -> None:
    assert main(["offline", "--output-dir", str(tmp_path), "--no-fail"]) == 0
    before = (tmp_path / "report.json").read_text(encoding="utf-8")

    assert main(["offline", "--output-dir", str(tmp_path), "--no-fail"]) == 2
    assert (tmp_path / "report.json").read_text(encoding="utf-8") == before
    assert main(["offline", "--output-dir", str(tmp_path), "--no-fail", "--overwrite"]) == 0


def test_cases_option_selects_specific_cases(tmp_path: Path) -> None:
    args = ["offline", "--output-dir", str(tmp_path), "--no-fail", "--cases", "eval-063,eval-076"]
    assert main(args) == 0
    report = _report(tmp_path)
    assert [c["case_id"] for c in report["per_case"]] == ["eval-063", "eval-076"]  # type: ignore[index, union-attr]


def test_unknown_case_ids_are_rejected(tmp_path: Path) -> None:
    assert main(["offline", "--output-dir", str(tmp_path), "--cases", "eval-999"]) == 2


def test_compare_reports_metric_deltas_and_case_changes(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    main(["offline", "--output-dir", str(first), "--no-fail"])
    main(["offline", "--output-dir", str(second), "--no-fail"])

    assert compare_main(["--baseline", str(first), "--candidate", str(second)]) == 0
    result = json.loads((second / "comparison.json").read_text(encoding="utf-8"))
    assert all(m["delta"] in (0, None) for m in result["metrics"])
    assert result["new_failures"] == [] and result["fixed_cases"] == []
    assert (second / "comparison.md").exists()


def test_unknown_chunk_reference_is_rejected(tmp_path: Path) -> None:
    row = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8").splitlines()[0])
    row["relevant_chunk_ids"] = ["missing-chunk"]
    row["evidence_groups"] = []
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text(json.dumps(row), encoding="utf-8")
    assert main(["offline", "--dataset", str(dataset), "--output-dir", str(tmp_path / "o")]) == 2
