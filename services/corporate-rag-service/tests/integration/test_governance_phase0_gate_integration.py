from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase0_exit_criteria_is_backed_by_required_artifacts():
    roadmap = _read("docs/production_grade_roadmap_v1.md")
    governance = _read("docs/development_governance.md")
    risk = _read("docs/production_risk_matrix.md")
    gate = _read("docs/release_gate_template.md")
    invariants = _read("docs/architectural_invariants.md")
    changelog = _read("CHANGELOG.md")

    assert "### Phase 0 — Governance Foundation" in roadmap
    assert "review_chain documented" in roadmap
    assert "production_risk_matrix exists" in roadmap
    assert "release_gate_template exists" in roadmap
    assert "architectural_invariants documented" in roadmap
    assert "changelog discipline enforced" in roadmap

    assert "Mandatory Review Sequence" in governance
    assert "Production Risk Matrix" in risk
    assert "Mandatory Checklist" in gate
    assert "architectural" in invariants.lower()
    assert "### Changed" in changelog


def test_phase0_gate_has_negative_guardrails_for_release_blockers():
    roadmap = _read("docs/production_grade_roadmap_v1.md")
    risk = _read("docs/production_risk_matrix.md")

    assert "No OpenAPI breaking changes." in roadmap
    assert "No feature removal without explicit decision." in roadmap
    assert "automatically NO-GO" in risk
