import uuid

import pytest

pytest.importorskip("pydantic")

from app.services.context_expansion import ContextExpansionEngine


class SeededRepo:
    def __init__(self, docs):
        self.docs = docs
        self.links = {}

    def fetch_document_neighbors(self, document_id: str, anchor_chunk_id: str, window: int = 1):
        chunks = self.docs[document_id]
        anchor = next(c for c in chunks if c["chunk_id"] == anchor_chunk_id)
        lo, hi = anchor["ordinal"] - window, anchor["ordinal"] + window
        return [c for c in chunks if lo <= c["ordinal"] <= hi]

    def fetch_outgoing_linked_documents(self, document_ids: list[str], max_docs: int):
        out = []
        for doc in document_ids:
            out.extend(self.links.get(doc, []))
        return out[:max_docs]

    def fetch_top_chunks_for_document(self, document_id: str, query_embedding: list[float], limit_n: int = 2):
        _ = query_embedding
        return self.docs.get(document_id, [])[:limit_n]


def _chunk(doc: str, cid: str, ordinal: int, score: float):
    return {
        "chunk_id": cid,
        "document_id": doc,
        "ordinal": ordinal,
        "final_score": score,
        "embedding": [1.0, 0.0] if doc.endswith("a") else [0.0, 1.0],
        "chunk_text": f"{doc}-{cid}",
        "token_count": 10,
        "heading_path": ["sec"],
    }


def test_expansion_yields_coherent_windows_with_seeded_docs(monkeypatch):
    doc_a = str(uuid.uuid4()) + "a"
    doc_b = str(uuid.uuid4())
    repo = SeededRepo(
        {
            doc_a: [_chunk(doc_a, "a1", 1, 0.9), _chunk(doc_a, "a2", 2, 0.3), _chunk(doc_a, "a3", 3, 0.2)],
            doc_b: [_chunk(doc_b, "b1", 1, 0.8), _chunk(doc_b, "b2", 2, 0.1)],
        }
    )

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_DOCS", 2)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_NEIGHBOR_WINDOW", 1)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS", 12)

    selected, _ = ContextExpansionEngine(repo).expand(
        final_query="query",
        base_candidates=[_chunk(doc_a, "a2", 2, 0.95), _chunk(doc_b, "b1", 1, 0.85)],
        token_budget=120,
        mode="doc_neighbor",
        query_embedding=[1.0, 0.0],
    )

    selected_ids = {x["chunk_id"] for x in selected}
    assert "a1" in selected_ids and "a3" in selected_ids
    assert "b2" in selected_ids
