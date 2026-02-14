from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.refactor_orchestrator import (
    WORKFLOW,
    CheckResult,
    WorkflowStage,
    _clip_output,
    classify_check,
    render_report,
    run_workflow,
)


def test_workflow_keeps_yaml_stage_order() -> None:
    assert [stage.stage for stage in WORKFLOW] == [
        "discovery",
        "requirements",
        "redesign_refactor",
        "simplify",
        "document",
        "verify",
    ]


def test_classify_check_returns_warn_for_missing_dependency_errors() -> None:
    assert classify_check(2, "ModuleNotFoundError: No module named 'pydantic'") == "warn"


def test_classify_check_returns_fail_for_generic_nonzero_error() -> None:
    assert classify_check(1, "assertion failed") == "fail"


def test_run_workflow_integration_records_stage_results() -> None:
    stages = (
        WorkflowStage("discovery", "agent-a", ("a",), ("python -c \"print('ok')\"",)),
        WorkflowStage("verify", "agent-b", ("b",), ("python -c \"import sys; print('boom'); sys.exit(1)\"",)),
    )

    results = run_workflow(stages, fail_fast=False)

    assert len(results) == 2
    assert results[0].status == "pass"
    assert results[1].status == "fail"
    assert "boom" in results[1].checks[0].output


def test_clip_output_truncates_old_lines() -> None:
    raw = "\n".join([f"line-{idx}" for idx in range(6)])
    clipped = _clip_output(raw, max_lines=3)
    assert "<clipped 3 lines>" in clipped
    assert "line-5" in clipped
    assert "line-0" not in clipped


def test_render_report_contains_table_and_clipped_statuses() -> None:
    report = render_report(
        [
            type("StageResultStub", (), {
                "stage": "discovery",
                "agent": "codebase-cartographer",
                "status": "pass",
                "checks": (CheckResult(command="pytest -q", status="pass", return_code=0, output="a\nb\nc\nd"),),
            })()
        ],
        max_output_lines=2,
    )

    assert "| stage | agent | checks | status |" in report
    assert "`pytest -q` → pass" in report
    assert "<clipped 2 lines>" in report
