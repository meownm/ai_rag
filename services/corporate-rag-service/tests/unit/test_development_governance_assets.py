from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_development_governance_review_chain_order_is_explicit():
    text = _read("docs/development_governance.md")
    expected = [
        "1. **Design Review**",
        "2. **Implementation**",
        "3. **Regression Review**",
        "4. **Architecture Review**",
        "5. **Quality Review**",
        "6. **Observability Review**",
        "7. **Production Risk Update**",
        "8. **Release Gate Decision**",
    ]
    positions = [text.index(item) for item in expected]
    assert positions == sorted(positions)


def test_release_gate_template_contains_required_checklist_and_decisions():
    text = _read("docs/release_gate_template.md")
    assert "All **P0** risks are closed" in text
    assert "Schema is consistent" in text
    assert "Retrieval behavior is deterministic" in text
    assert "Token budget constraints are enforced" in text
    assert "Versioning is correct" in text
    assert "Logs are structured JSON" in text
    assert "Audit event is present" in text
    assert "GO" in text
    assert "GO WITH LIMITATIONS" in text
    assert "NO-GO" in text


def test_production_risk_matrix_contains_severities_and_p0_blocker_rule():
    text = _read("docs/production_risk_matrix.md")
    for severity in ("P0", "P1", "P2"):
        assert severity in text
    assert "Release gate is blocked while any **P0** risk remains open" in text
    assert "A release decision is **automatically NO-GO**" in text


def test_architectural_invariants_documented_and_referenced_by_release_gate():
    invariants = _read("docs/architectural_invariants.md")
    required_invariants = [
        "Source versions immutable",
        "Tombstone only after authoritative listing",
        "Deterministic retrieval",
        "Strict token budget",
        "Citation grounding",
        "Tenant isolation",
    ]
    for invariant in required_invariants:
        assert invariant in invariants

    template = _read("docs/release_gate_template.md")
    assert "docs/architectural_invariants.md" in template


def test_changelog_uses_keep_a_changelog_categories_and_records_epic_update():
    changelog = _read("CHANGELOG.md")
    for category in ("### Added", "### Changed", "### Fixed", "### Removed", "### Security"):
        assert category in changelog
    assert "EPIC" in changelog or "governance" in changelog.lower()


def _extract_open_risks_rows(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    start = lines.index("## Open Risks")
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("| RISK-"):
            rows.append(line)
    return rows


def test_production_risk_matrix_has_no_open_p0_rows():
    text = _read("docs/production_risk_matrix.md")
    open_rows = _extract_open_risks_rows(text)
    assert open_rows
    assert all("| P0 |" not in row for row in open_rows)


def test_development_governance_stop_points_are_defined_in_order():
    text = _read("docs/development_governance.md")
    ordered = [
        "GOV-SP1-REVIEW-CHAIN-DOC",
        "GOV-SP2-RISK-MATRIX-LIVE",
        "GOV-SP3-RELEASE-GATE-TEMPLATE",
        "GOV-SP4-CHANGELOG-DISCIPLINE",
        "GOV-SP5-ARCHITECTURAL-INVARIANTS",
        "GOV-SP6-GOLDEN-RETRIEVAL-SUITE",
        "GOV-SP7-OBSERVABILITY-CHECK",
    ]
    positions = [text.index(item) for item in ordered]
    assert positions == sorted(positions)


def test_release_gate_simulation_references_real_commit_sha():
    text = _read("docs/release_gate_simulation_epic_development_governance.md")
    assert "Commit SHA:" in text
    assert "pending" not in text.lower()


def test_roadmap_phase_order_and_gate_names_are_documented():
    text = _read("docs/production_grade_roadmap_v1.md")
    phases = [
        "### Phase 0 — Governance Foundation",
        "### Phase 1 — Integrity Hardening",
        "### Phase 2 — Observability Hardening",
        "### Phase 3 — Quality Stabilization",
        "### Phase 4 — Performance & Scale Hardening",
        "### Phase 5 — Release v1.0 Cut",
    ]
    positions = [text.index(phase) for phase in phases]
    assert positions == sorted(positions)

    for gate in (
        "Governance Gate",
        "Integrity Gate",
        "Observability Gate",
        "Quality Gate",
        "Performance Gate",
        "Production Gate",
    ):
        assert gate in text


def test_roadmap_global_constraints_include_non_regression_rules():
    text = _read("docs/production_grade_roadmap_v1.md")
    assert "No OpenAPI breaking changes." in text
    assert "No feature removal without explicit decision." in text
    assert "All invariants enforced by tests." in text
    assert "CI must fail on invariant violations." in text


def test_release_gate_template_tracks_implementation_verdict():
    text = _read("docs/release_gate_template.md")
    assert "Implementation verdict:" in text
