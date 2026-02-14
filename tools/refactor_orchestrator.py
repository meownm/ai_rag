from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence


WARN_PATTERNS = (
    "ModuleNotFoundError",
    "No module named",
    "missing dependencies",
)

DEFAULT_REPORT_MAX_LINES = 120


@dataclass(frozen=True)
class WorkflowStage:
    stage: str
    agent: str
    outputs: tuple[str, ...]
    checks: tuple[str, ...]


@dataclass(frozen=True)
class CheckResult:
    command: str
    status: str
    return_code: int
    output: str


@dataclass(frozen=True)
class StageResult:
    stage: str
    agent: str
    status: str
    checks: tuple[CheckResult, ...]


# YAML order copied from docs/agent_orchestration_guide.md and must not be reordered.
WORKFLOW: tuple[WorkflowStage, ...] = (
    WorkflowStage("discovery", "codebase-cartographer", ("module_map", "call_graph", "risk_hotspots"), ("pytest -q",)),
    WorkflowStage("requirements", "requirements-miner", ("requirements_catalog", "traceability_matrix", "extension_candidates"), ("pytest -q",)),
    WorkflowStage("redesign_refactor", "refactor-architect", ("refactor_plan", "migration_strategy", "pr_batches"), ("pytest -q",)),
    WorkflowStage("simplify", "duplication-slayer", ("duplication_registry", "simplification_patches"), ("pytest -q",)),
    WorkflowStage("document", "contract-scribe", ("updated_contracts", "updated_algorithm_docs", "updated_data_structures_docs"), ("pytest -q",)),
    WorkflowStage("verify", "quality-gatekeeper", ("gate_report", "release_recommendation"), ("pytest -q", "python tools/drift_check.py")),
)


def classify_check(return_code: int, output: str) -> str:
    if return_code == 0:
        return "pass"
    if any(pattern in output for pattern in WARN_PATTERNS):
        return "warn"
    return "fail"


def run_check(command: str, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> CheckResult:
    completed = runner(
        command,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    status = classify_check(completed.returncode, output)
    return CheckResult(command=command, status=status, return_code=completed.returncode, output=output)


def run_stage(stage: WorkflowStage, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> StageResult:
    check_results = tuple(run_check(command, runner=runner) for command in stage.checks)
    if any(check.status == "fail" for check in check_results):
        stage_status = "fail"
    elif any(check.status == "warn" for check in check_results):
        stage_status = "warn"
    else:
        stage_status = "pass"
    return StageResult(stage=stage.stage, agent=stage.agent, status=stage_status, checks=check_results)


def run_workflow(
    stages: Sequence[WorkflowStage],
    fail_fast: bool,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[StageResult, ...]:
    results: list[StageResult] = []
    for stage in stages:
        result = run_stage(stage, runner=runner)
        results.append(result)
        if fail_fast and result.status == "fail":
            break
    return tuple(results)


def _clip_output(output: str, max_lines: int) -> str:
    lines = (output or "<no output>").rstrip().splitlines()
    if max_lines <= 0 or len(lines) <= max_lines:
        return "\n".join(lines)
    hidden = len(lines) - max_lines
    tail = lines[-max_lines:]
    return "\n".join([f"<clipped {hidden} lines>", *tail])


def render_report(results: Sequence[StageResult], max_output_lines: int = DEFAULT_REPORT_MAX_LINES) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Refactor Orchestrator Run Report",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "| stage | agent | checks | status |",
        "|---|---|---|---|",
    ]
    for result in results:
        check_str = "<br>".join(f"`{check.command}` → {check.status}" for check in result.checks)
        lines.append(f"| {result.stage} | {result.agent} | {check_str} | {result.status} |")
    lines.append("")
    lines.append("## Check outputs")
    for result in results:
        lines.append("")
        lines.append(f"### {result.stage}")
        for check in result.checks:
            lines.append("")
            lines.append(f"#### `{check.command}` ({check.status}, rc={check.return_code})")
            lines.append("```")
            lines.append(_clip_output(check.output, max_output_lines))
            lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the strict YAML-ordered refactor orchestration workflow.")
    parser.add_argument(
        "--report",
        default="docs/implementation/refactor_orchestrator_run.md",
        help="Where to write the markdown report.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first failed stage.",
    )
    parser.add_argument(
        "--max-output-lines",
        type=int,
        default=DEFAULT_REPORT_MAX_LINES,
        help="Maximum lines saved per check output section (0 disables clipping).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = run_workflow(WORKFLOW, fail_fast=args.fail_fast)
    report = render_report(results, max_output_lines=args.max_output_lines)
    write_report(Path(args.report), report)
    if any(stage.status == "fail" for stage in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
