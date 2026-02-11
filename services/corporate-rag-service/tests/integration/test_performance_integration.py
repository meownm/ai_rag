from app.services.performance import summarize_perf


def test_perf_p95_report_from_fixture_samples():
    samples = []
    for i in range(1, 41):
        samples.append(
            {
                "t_parse_ms": 5 + i,
                "t_lexical_ms": 10 + i,
                "t_vector_ms": 20 + i,
                "t_rerank_ms": 7 + i,
                "t_total_ms": 60 + i,
                "t_llm_ms": 0,
                "t_citations_ms": 1 + (i % 3),
            }
        )

    report = summarize_perf(samples)
    assert report["t_total_ms_p95"] > 90
    assert report["t_lexical_ms_p95"] > 40
