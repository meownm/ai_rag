# Production Risk Matrix

Version: 1.0.0  
Status: Living Artifact (mandatory update before every release)  
Last Updated: 2026-02-12

## Policy

- The matrix **must be updated before every release gate decision**.
- Release gate is blocked while any **P0** risk remains open.
- Risk state transitions are tracked in three sections: Open, Mitigated, Closed.

## Severity Definitions

- **P0 (Critical)**: High probability/high impact risks that can cause major outage, security breach, data corruption, or tenant-isolation failure. Release is forbidden with open P0.
- **P1 (High)**: Significant risks with bounded blast radius or available mitigations. May release only with explicit limitations and owner-approved mitigation timeline.
- **P2 (Moderate)**: Manageable risks with low expected impact, tracked for planned remediation.

## Open Risks

| Risk ID | Severity | Description | Owner | Detection | Mitigation Plan | Target Date |
|---|---|---|---|---|---|---|
| RISK-001 | P1 | Potential retrieval quality drift if ranking weights are changed without golden-suite baseline refresh. | quality | Golden suite failures / trend monitoring | Require golden suite approval in review chain and block merge on regression. | 2026-02-28 |

## Mitigated Risks

| Risk ID | Severity | Description | Mitigation Applied | Verification Evidence | Owner |
|---|---|---|---|---|---|
| RISK-002 | P1 | Missing mandatory observability events in some flows. | Added mandatory observability CI checks for request lifecycle, context assembly, and LLM completion events. | `tests/integration/test_observability_required_events_integration.py` | observability |

## Closed Risks

| Risk ID | Former Severity | Description | Closure Rationale | Closed On | Owner |
|---|---|---|---|---|---|
| RISK-000 | P0 | Undefined release governance sequence. | Formal review chain and release gate artifacts introduced and mandated. | 2026-02-12 | release |

## Release Blocking Rule

A release decision is **automatically NO-GO** when at least one item in **Open Risks** has severity **P0**.
