from app.services.scoring_trace import build_scoring_trace


def test_build_scoring_trace_contains_required_fields_positive():
    trace = build_scoring_trace(
        "trace-123",
        [
            {
                "chunk_id": "11111111-1111-1111-1111-111111111111",
                "lex_score": 0.6,
                "vec_score": 0.7,
                "rerank_score": 0.8,
                "boosts_applied": [{"name": "author_presence", "value": 0.05}],
                "final_score": 0.69,
                "rank_position": 1,
            }
        ],
    )

    assert trace["trace_id"] == "trace-123"
    entry = trace["scoring_trace"][0]
    assert set(["lex_score", "vec_score", "rerank_score", "boosts_applied", "final_score", "rank_position", "chunk_id"]).issubset(entry)


def test_build_scoring_trace_negative_defaults_when_missing():
    trace = build_scoring_trace("trace-x", [{"chunk_id": "a"}])
    entry = trace["scoring_trace"][0]
    assert entry["lex_score"] == 0.0
    assert entry["vec_score"] == 0.0
    assert entry["rerank_score"] == 0.0
    assert entry["boosts_applied"] == []
