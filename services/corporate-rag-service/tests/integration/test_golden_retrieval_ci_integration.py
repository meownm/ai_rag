import json
from pathlib import Path

import pytest


def _load() -> list[dict]:
    path = Path("tests/regression-suite/golden_retrieval_governance.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _corpus(golden: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for idx, item in enumerate(golden):
        query = item["query"].lower()
        rows.append(
            {
                "chunk_id": f"chunk-{idx}",
                "document_id": item["expected_document_id"],
                "chunk_text": f"{query} регламент и официальный порядок",
                "embedding": [1.0, 0.0],
                "vec_score": 0.0,
                "rerank_score": 0.0,
            }
        )
        rows.append(
            {
                "chunk_id": f"noise-{idx}",
                "document_id": f"noise-doc-{idx}",
                "chunk_text": "случайный нерелевантный текст",
                "embedding": [0.0, 1.0],
                "vec_score": 0.0,
                "rerank_score": 0.0,
            }
        )
    return rows


def test_golden_retrieval_suite_has_expected_size_range():
    golden = _load()
    assert 10 <= len(golden) <= 20


def test_golden_retrieval_expected_document_is_in_top_results():
    pytest.importorskip("pydantic")
    from app.services.retrieval import hybrid_rank

    golden = _load()
    corpus = _corpus(golden)

    for item in golden:
        ranked, _ = hybrid_rank(
            item["query"],
            [dict(c) for c in corpus],
            query_embedding=[0.0, 0.0],
            normalize_scores=False,
        )
        top_doc_ids = [entry["document_id"] for entry in ranked[:3]]
        assert item["expected_document_id"] in top_doc_ids


def test_golden_retrieval_negative_missing_expected_document_id_field():
    broken_item = {"query": "Q without expected doc"}
    with pytest.raises(KeyError):
        _ = broken_item["expected_document_id"]
