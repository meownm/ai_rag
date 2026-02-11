from app.services.performance import build_stage_budgets, exceeded_budgets, summarize_perf


def test_build_stage_budgets_from_env_timeouts_positive():
    budgets = build_stage_budgets(30, 10)
    assert budgets["t_total_ms"] == 30000
    assert budgets["t_vector_ms"] <= 10000


def test_exceeded_budgets_negative_detection():
    perf = {"t_total_ms": 120, "t_parse_ms": 15}
    budgets = {"t_total_ms": 100, "t_parse_ms": 20}
    exceeded = exceeded_budgets(perf, budgets)
    assert "t_total_ms" in exceeded
    assert "t_parse_ms" not in exceeded


def test_summarize_perf_p95_from_fixture_samples():
    samples = [
        {"t_total_ms": 100, "t_parse_ms": 10, "t_lexical_ms": 20, "t_vector_ms": 40, "t_rerank_ms": 15, "t_llm_ms": 0, "t_citations_ms": 2},
        {"t_total_ms": 110, "t_parse_ms": 11, "t_lexical_ms": 21, "t_vector_ms": 41, "t_rerank_ms": 16, "t_llm_ms": 0, "t_citations_ms": 2},
        {"t_total_ms": 130, "t_parse_ms": 15, "t_lexical_ms": 30, "t_vector_ms": 50, "t_rerank_ms": 20, "t_llm_ms": 0, "t_citations_ms": 3},
        {"t_total_ms": 170, "t_parse_ms": 30, "t_lexical_ms": 45, "t_vector_ms": 60, "t_rerank_ms": 30, "t_llm_ms": 0, "t_citations_ms": 4},
    ]
    summary = summarize_perf(samples)
    assert summary["t_total_ms_p95"] >= 130
    assert summary["t_vector_ms_p95"] >= 50
