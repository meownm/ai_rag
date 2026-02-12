import json
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from app.services.context_expansion import ContextExpansionEngine
from app.services.retrieval import hybrid_rank


def _load_golden() -> list[dict]:
    return json.loads(Path(__file__).with_name("golden_queries.json").read_text(encoding="utf-8"))


def _build_corpus(golden_set: list[dict]) -> list[dict]:
    corpus: list[dict] = []
    for idx, item in enumerate(golden_set):
        citation = item["expected_citations"][0]
        query_terms = item["query"].lower().split()
        primary_text = f"policy {' '.join(query_terms)} authoritative details section {idx}"
        corpus.append(
            {
                "chunk_id": citation["chunk_id"],
                "document_id": citation["doc_id"],
                "chunk_text": primary_text,
                "embedding": [1.0, 0.0],
                "vec_score": 0.0,
                "rerank_score": 0.0,
            }
        )

        # deterministic distractor chunk per query
        corpus.append(
            {
                "chunk_id": f"noise-{idx}",
                "document_id": f"noise-doc-{idx}",
                "chunk_text": f"unrelated handbook entry {idx} generic text",
                "embedding": [0.0, 1.0],
                "vec_score": 0.0,
                "rerank_score": 0.0,
            }
        )
    return corpus


def _run_retrieval(query: str, corpus: list[dict]) -> list[dict]:
    ranked, _ = hybrid_rank(query, [dict(item) for item in corpus], query_embedding=[0.0, 0.0], normalize_scores=False)
    return ranked


def test_golden_set_shape_and_size():
    golden_set = _load_golden()
    assert len(golden_set) == 31
    for item in golden_set:
        assert item["query"]
        assert item["expected_top_documents"]
        assert item["expected_citations"]
        assert 0 <= float(item["min_confidence"]) <= 1
        if "expected_neighbor_chunk_id" in item:
            assert item["expected_neighbor_chunk_id"]


def test_retrieval_matches_regression_golden_set():
    golden_set = _load_golden()
    corpus = _build_corpus(golden_set)
    for item in golden_set:
        ranked = _run_retrieval(item["query"], corpus)
        top = ranked[0]
        expected_doc = item["expected_top_documents"][0]
        expected_citation = item["expected_citations"][0]

        assert top["document_id"] == expected_doc
        assert top["chunk_id"] == expected_citation["chunk_id"]
        assert float(top.get("final_score", 0.0)) >= float(item["min_confidence"])


def test_golden_set_citations_are_unique():
    golden_set = _load_golden()
    seen = set()
    for item in golden_set:
        citation = item["expected_citations"][0]
        key = (citation["doc_id"], citation["chunk_id"])
        assert key not in seen
        seen.add(key)


def test_golden_neighbor_expectations_are_expandable():
    golden_set = _load_golden()
    for item in golden_set:
        expected_neighbor = item.get("expected_neighbor_chunk_id")
        if not expected_neighbor:
            continue

        citation = item["expected_citations"][0]
        doc_id = citation["doc_id"]
        anchor_id = citation["chunk_id"]

        class _Repo:
            @staticmethod
            def fetch_document_neighbors(document_id: str, anchor_chunk_id: str, window: int = 1):
                if document_id == doc_id and anchor_chunk_id == anchor_id and window == 1:
                    return [
                        {
                            "chunk_id": anchor_id,
                            "document_id": doc_id,
                            "ordinal": 2,
                            "final_score": 0.95,
                            "embedding": [1.0, 0.0],
                            "chunk_text": "anchor",
                            "token_count": 10,
                            "heading_path": ["section"],
                        },
                        {
                            "chunk_id": expected_neighbor,
                            "document_id": doc_id,
                            "ordinal": 3,
                            "final_score": 0.3,
                            "embedding": [0.9, 0.1],
                            "chunk_text": "neighbor",
                            "token_count": 10,
                            "heading_path": ["section"],
                        },
                    ]
                return []

            @staticmethod
            def fetch_outgoing_linked_documents(_document_ids: list[str], _max_docs: int):
                return []

            @staticmethod
            def fetch_top_chunks_for_document(_document_id: str, _query_embedding: list[float], limit_n: int = 2):
                _ = limit_n
                return []

        selected, _ = ContextExpansionEngine(_Repo()).expand(
            final_query=item["query"],
            base_candidates=[
                {
                    "chunk_id": anchor_id,
                    "document_id": doc_id,
                    "ordinal": 2,
                    "final_score": 0.95,
                    "embedding": [1.0, 0.0],
                    "chunk_text": "anchor",
                    "token_count": 10,
                    "heading_path": ["section"],
                }
            ],
            token_budget=200,
            mode="doc_neighbor",
            query_embedding=[1.0, 0.0],
        )

        assert expected_neighbor in {c["chunk_id"] for c in selected}
