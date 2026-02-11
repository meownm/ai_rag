from statistics import quantiles
from typing import Any


def build_stage_budgets(request_timeout_seconds: int, embeddings_timeout_seconds: int) -> dict[str, int]:
    total_budget_ms = request_timeout_seconds * 1000
    vector_budget_ms = min(total_budget_ms, embeddings_timeout_seconds * 1000)
    # Derived configurable budgets from existing env-backed timeouts.
    return {
        "t_parse_ms": max(10, int(total_budget_ms * 0.05)),
        "t_lexical_ms": max(10, int(total_budget_ms * 0.20)),
        "t_vector_ms": max(10, int(vector_budget_ms * 0.60)),
        "t_rerank_ms": max(10, int(total_budget_ms * 0.25)),
        "t_total_ms": total_budget_ms,
        "t_llm_ms": max(10, int(total_budget_ms * 0.35)),
        "t_citations_ms": max(10, int(total_budget_ms * 0.10)),
    }


def exceeded_budgets(perf: dict[str, int], budgets: dict[str, int]) -> dict[str, dict[str, int]]:
    exceeded: dict[str, dict[str, int]] = {}
    for key, budget in budgets.items():
        actual = int(perf.get(key, 0))
        if actual > budget:
            exceeded[key] = {"actual": actual, "budget": budget}
    return exceeded


def p95(values: list[int]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    return float(quantiles(values, n=20, method="inclusive")[18])


def summarize_perf(samples: list[dict[str, Any]]) -> dict[str, float]:
    keys = ["t_parse_ms", "t_lexical_ms", "t_vector_ms", "t_rerank_ms", "t_total_ms", "t_llm_ms", "t_citations_ms"]
    return {f"{k}_p95": p95([int(s.get(k, 0)) for s in samples]) for k in keys}
