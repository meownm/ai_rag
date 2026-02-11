from app.services.retrieval import hybrid_rank


def test_hybrid_rank_preserves_db_lex_score_for_bm25_ordering():
    query_embedding = [1.0, 0.0]
    candidates = [
        {
            "chunk_id": "a",
            "chunk_text": "irrelevant text",
            "embedding": [1.0, 0.0],
            "lex_score": 0.95,
            "author": None,
        },
        {
            "chunk_id": "b",
            "chunk_text": "query terms maybe",
            "embedding": [1.0, 0.0],
            "lex_score": 0.10,
            "author": None,
        },
    ]

    ranked, _ = hybrid_rank("vacation policy", candidates, query_embedding)

    assert ranked[0]["chunk_id"] == "a"
    assert ranked[0]["lex_score"] == 0.95
    assert ranked[1]["lex_score"] == 0.10
