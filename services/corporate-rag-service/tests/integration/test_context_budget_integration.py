from app.services.query_pipeline import apply_context_budget


def test_large_chunk_set_respects_token_budget_integration():
    chunks = [
        {"chunk_id": str(i), "chunk_text": ("token " * 300), "final_score": 1.0 - (i * 0.01), "rank_position": i + 1}
        for i in range(10)
    ]
    retained, log = apply_context_budget(chunks, use_token_budget_assembly=True, max_context_tokens=600)

    assert retained
    assert log["total_context_tokens_est"] <= 600
    assert log["max_context_tokens"] == 600
