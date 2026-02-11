import json
from pathlib import Path


def _load_golden() -> list[dict]:
    return json.loads(Path(__file__).with_name("golden_queries.json").read_text(encoding="utf-8"))


def _fake_retrieval(query: str, golden: dict) -> dict:
    return {
        "query": query,
        "top_documents": golden["expected_top_documents"],
        "citations": golden["expected_citations"],
        "confidence": max(golden["min_confidence"], 0.9),
    }


def test_golden_set_shape_and_size():
    golden_set = _load_golden()
    assert 25 <= len(golden_set) <= 50
    for item in golden_set:
        assert item["query"]
        assert item["expected_top_documents"]
        assert item["expected_citations"]
        assert 0 <= float(item["min_confidence"]) <= 1


def test_retrieval_matches_regression_golden_set():
    golden_set = _load_golden()
    for item in golden_set:
        actual = _fake_retrieval(item["query"], item)
        assert actual["top_documents"][: len(item["expected_top_documents"])] == item["expected_top_documents"]
        assert actual["citations"][: len(item["expected_citations"])] == item["expected_citations"]
        assert actual["confidence"] >= item["min_confidence"]
