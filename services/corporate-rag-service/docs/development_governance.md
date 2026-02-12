# Development Governance: Multi-Agent Review Chain

Version: 1.0.0  
Status: Active  
Last Updated: 2026-02-12

## Purpose

This document formalizes the lightweight and automatable review chain required before any production release. The process introduces explicit stop points without changing runtime API behavior.

## Mandatory Review Sequence (No Reordering Allowed)

Every EPIC and release candidate **must** pass the following sequence in this exact order:

1. **Design Review** (owner: Design Agent)
2. **Implementation** (owner: Implementation Agent)
3. **Regression Review** (owner: Regression Review Agent)
4. **Architecture Review** (owner: Architecture Integrity Agent)
5. **Quality Review** (owner: Retrieval & Context Quality Agent)
6. **Observability Review** (owner: Observability & Audit Agent)
7. **Production Risk Update** (owner: Performance & Scale Agent)
8. **Release Gate Decision** (owner: Release Authority Agent)

If any step fails, the process returns to Implementation Agent for remediation and restarts from the first failed step.

## Stage Inputs and Outputs

### 1) Design Review
- Input: EPIC scope, constraints, acceptance criteria.
- Output: approved implementation plan + required docs/tests delta.

### 2) Implementation
- Input: approved design plan.
- Output: code, tests, and documentation updates bound to scope.

### 3) Regression Review
- Input: changed code and tests.
- Output: regression verdict and gap list.

### 4) Architecture Review
- Input: design changes + invariants impact.
- Output: architecture compliance verdict.

### 5) Quality Review
- Input: retrieval behavior, golden suite status.
- Output: quality verdict and quality drift notes.

### 6) Observability Review
- Input: structured logs, required events, schema checks.
- Output: observability compliance verdict.

### 7) Production Risk Update
- Input: latest implementation and review findings.
- Output: updated `docs/production_risk_matrix.md`.

### 8) Release Gate Decision
- Input: all prior stage verdicts + risk matrix.
- Output: one decision: **GO / GO WITH LIMITATIONS / NO-GO**.


## Stop Points (EPIC YAML Order)

The governance chain is bound to the EPIC stop points and must follow YAML order strictly:

1. `GOV-SP1-REVIEW-CHAIN-DOC`
2. `GOV-SP2-RISK-MATRIX-LIVE`
3. `GOV-SP3-RELEASE-GATE-TEMPLATE`
4. `GOV-SP4-CHANGELOG-DISCIPLINE`
5. `GOV-SP5-ARCHITECTURAL-INVARIANTS`
6. `GOV-SP6-GOLDEN-RETRIEVAL-SUITE`
7. `GOV-SP7-OBSERVABILITY-CHECK`

## Acceptance Gate Checklist Template

Use this checklist verbatim for every release candidate:

- [ ] Design Review completed and approved.
- [ ] Implementation completed and evidence recorded.
- [ ] Regression Review completed and approved.
- [ ] Architecture Review completed and approved.
- [ ] Quality Review completed and approved.
- [ ] Observability Review completed and approved.
- [ ] Production Risk Matrix updated for this release candidate.
- [ ] No open P0 risks in Production Risk Matrix.
- [ ] Release Gate decision recorded with rationale.

## Automation Guidance

- Treat each stage output as a versioned repository artifact (documents + tests).
- CI should fail when required stage artifacts are missing.
- CI should fail when mandatory tests for retrieval and observability fail.
- PRs should include links to the updated governance artifacts.
