import uuid

import pytest

pytest.importorskip("pydantic")

from app.services.context_expansion import ContextExpansionEngine


class FakeRepo:
    def __init__(self):
        self.neighbors = {}
        self.linked_docs = []
        self.linked_chunks = {}

    def fetch_document_neighbors(self, document_id: str, anchor_chunk_id: str, window: int = 1):
        return list(self.neighbors.get((document_id, anchor_chunk_id, window), []))

    def fetch_outgoing_linked_documents(self, document_ids: list[str], max_docs: int):
        _ = document_ids
        return self.linked_docs[:max_docs]

    def fetch_top_chunks_for_document(self, document_id: str, query_embedding: list[float], limit_n: int = 2):
        _ = query_embedding
        return list(self.linked_chunks.get(document_id, []))[:limit_n]


def _cand(chunk_id: str, doc_id: str, ordinal: int, score: float, emb: list[float], text: str = "text"):
    return {
        "chunk_id": chunk_id,
        "document_id": doc_id,
        "ordinal": ordinal,
        "final_score": score,
        "embedding": emb,
        "chunk_text": text,
        "token_count": 20,
        "heading_path": ["h1"],
    }


def test_neighbor_expansion_adds_window_chunks(monkeypatch):
    repo = FakeRepo()
    doc_id = str(uuid.uuid4())
    anchor = _cand("a", doc_id, 2, 0.9, [1.0, 0.0], "anchor")
    repo.neighbors[(doc_id, "a", 1)] = [_cand("n1", doc_id, 1, 0.1, [0.9, 0.0]), _cand("a", doc_id, 2, 0.9, [1.0, 0.0]), _cand("n2", doc_id, 3, 0.1, [0.8, 0.0])]

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_TOPK_BASE", 8)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_TOPK_HARD_CAP", 20)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_DOCS", 4)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_NEIGHBOR_WINDOW", 1)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS", 12)

    selected, debug = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=[anchor],
        token_budget=200,
        mode="doc_neighbor",
        query_embedding=[1.0, 0.0],
    )

    ids = {c["chunk_id"] for c in selected}
    assert {"a", "n1", "n2"}.issubset(ids)
    assert debug.expanded_from_neighbors_count == 2


def test_doc_limit_and_extra_chunks_cap_enforced(monkeypatch):
    repo = FakeRepo()
    doc_a, doc_b = str(uuid.uuid4()), str(uuid.uuid4())
    base = [_cand("a1", doc_a, 1, 0.9, [1, 0]), _cand("b1", doc_b, 1, 0.8, [0, 1])]
    repo.neighbors[(doc_a, "a1", 1)] = [_cand("a2", doc_a, 2, 0.2, [1, 0.1])]
    repo.neighbors[(doc_b, "b1", 1)] = [_cand("b2", doc_b, 2, 0.2, [0.1, 1])]

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_DOCS", 1)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS", 1)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_NEIGHBOR_WINDOW", 1)

    selected, _ = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=base,
        token_budget=200,
        mode="doc_neighbor",
        query_embedding=[1.0, 0.0],
    )

    ids = {c["chunk_id"] for c in selected}
    assert "a2" in ids
    assert "b2" not in ids


def test_redundancy_filter_removes_near_duplicates(monkeypatch):
    repo = FakeRepo()
    doc = str(uuid.uuid4())
    base = [_cand("a1", doc, 1, 0.9, [1, 0]), _cand("a2", doc, 2, 0.8, [1, 0.001])]

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_REDUNDANCY_SIM_THRESHOLD", 0.92)

    selected, debug = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=base,
        token_budget=200,
        mode="doc_neighbor",
        query_embedding=[1.0, 0.0],
    )

    assert len(selected) == 1
    assert debug.redundancy_filtered_count >= 1


def test_deterministic_ordering_for_same_inputs():
    repo = FakeRepo()
    doc = str(uuid.uuid4())
    base = [_cand("b", doc, 2, 0.7, [0.8, 0.1]), _cand("a", doc, 1, 0.9, [0.9, 0.1])]

    engine = ContextExpansionEngine(repo)
    first, _ = engine.expand(final_query="q", base_candidates=base, token_budget=200, mode="doc_neighbor", query_embedding=[1, 0])
    second, _ = engine.expand(final_query="q", base_candidates=base, token_budget=200, mode="doc_neighbor", query_embedding=[1, 0])

    assert [c["chunk_id"] for c in first] == [c["chunk_id"] for c in second]


def test_link_mode_includes_linked_doc_chunks(monkeypatch):
    repo = FakeRepo()
    doc_a = str(uuid.uuid4())
    doc_link = str(uuid.uuid4())
    base = [_cand("a1", doc_a, 1, 0.9, [1, 0])]
    repo.linked_docs = [doc_link]
    repo.linked_chunks[doc_link] = [_cand("l1", doc_link, 1, 0.6, [0.1, 1.0])]

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_LINK_DOCS", 1)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS", 12)

    selected, debug = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=base,
        token_budget=200,
        mode="doc_neighbor_plus_links",
        query_embedding=[1, 0],
    )

    assert "l1" in {c["chunk_id"] for c in selected}
    assert debug.expanded_from_links_count == 1


def test_link_mode_skips_links_when_doc_depth_is_sufficient():
    repo = FakeRepo()
    doc_a = str(uuid.uuid4())
    doc_link = str(uuid.uuid4())
    base = [_cand("a1", doc_a, 1, 0.9, [1, 0]), _cand("a2", doc_a, 2, 0.8, [1, 0.1])]
    repo.linked_docs = [doc_link]
    repo.linked_chunks[doc_link] = [_cand("l1", doc_link, 1, 0.6, [0.1, 1.0])]

    selected, debug = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=base,
        token_budget=200,
        mode="doc_neighbor_plus_links",
        query_embedding=[1, 0],
    )

    assert "l1" not in {c["chunk_id"] for c in selected}
    assert debug.expanded_from_links_count == 0


def test_doc_neighbor_preserves_document_rank_then_ordinal():
    repo = FakeRepo()
    doc_high, doc_low = str(uuid.uuid4()), str(uuid.uuid4())
    base = [
        _cand("l1", doc_low, 1, 0.4, [0, 1]),
        _cand("h2", doc_high, 2, 0.9, [1, 0]),
        _cand("h1", doc_high, 1, 0.85, [1, 0.1]),
    ]

    selected, _ = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=base,
        token_budget=200,
        mode="doc_neighbor",
        query_embedding=[1, 0],
    )

    assert [c["chunk_id"] for c in selected] == ["h1", "h2", "l1"]


def test_neighbor_mode_adds_neighbors_without_links(monkeypatch):
    repo = FakeRepo()
    doc_a = str(uuid.uuid4())
    base = [_cand("a1", doc_a, 2, 0.9, [1, 0])]
    repo.neighbors[(doc_a, "a1", 1)] = [_cand("a0", doc_a, 1, 0.1, [0.9, 0]), _cand("a2", doc_a, 3, 0.1, [0.8, 0.1])]

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_NEIGHBOR_WINDOW", 1)
    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS", 12)

    selected, debug = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=base,
        token_budget=200,
        mode="neighbor",
        query_embedding=[1, 0],
    )

    assert {"a0", "a1", "a2"}.issubset({c["chunk_id"] for c in selected})
    assert debug.expanded_from_links_count == 0


def test_budget_stop_recorded_when_chunk_overflow(monkeypatch):
    repo = FakeRepo()
    doc = str(uuid.uuid4())
    big = _cand("big", doc, 1, 0.9, [1, 0], text="x" * 100)
    big["token_count"] = 500

    monkeypatch.setattr("app.services.context_expansion.settings.CONTEXT_EXPANSION_MIN_GAIN", 0.0)

    selected, debug = ContextExpansionEngine(repo).expand(
        final_query="q",
        base_candidates=[big],
        token_budget=10,
        mode="off",
        query_embedding=[1, 0],
    )

    assert selected == []
    assert any(step.startswith("stop:budget") for step in debug.context_selection_steps)
