import uuid

import pytest

pytest.importorskip("sqlalchemy")

from app.db.repositories import TenantRepository


class FakeQuery:
    def __init__(self, first_result=None, all_result=None):
        self.filters = []
        self.order_bys = []
        self.first_result = first_result
        self.all_result = all_result or []
        self.limit_value = None

    def join(self, *_args, **_kwargs):
        return self

    def filter(self, criterion):
        self.filters.append(str(criterion))
        return self

    def order_by(self, *args):
        self.order_bys.extend(str(a) for a in args)
        return self

    def limit(self, limit_n):
        self.limit_value = limit_n
        return self

    def all(self):
        return self.all_result

    def first(self):
        return self.first_result


class FakeDB:
    def __init__(self):
        self.queries = []

    def query(self, *_args, **_kwargs):
        q = FakeQuery()
        self.queries.append(q)
        return q


def test_fetch_document_neighbors_never_crosses_doc_boundary():
    db = FakeDB()
    repo = TenantRepository(db, str(uuid.uuid4()))

    anchor_query = FakeQuery(first_result=type("Anchor", (), {"ordinal": 10})())
    neighbors_query = FakeQuery(all_result=[])
    db.queries = [anchor_query, neighbors_query]
    db.query = lambda *_args, **_kwargs: db.queries.pop(0)

    _ = repo.fetch_document_neighbors("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", window=2)

    assert any("chunks.document_id = :document_id_1" in f for f in neighbors_query.filters)
    assert any("chunks.ordinal >= :ordinal_1" in f for f in neighbors_query.filters)
    assert any("chunks.ordinal <= :ordinal_1" in f or "chunks.ordinal <= :ordinal_2" in f for f in neighbors_query.filters)


def test_fetch_outgoing_linked_documents_is_deterministic_and_limited():
    db = FakeDB()
    repo = TenantRepository(db, str(uuid.uuid4()))

    rows = [(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),), (uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),)]
    q = FakeQuery(all_result=rows)
    db.query = lambda *_args, **_kwargs: q

    linked = repo.fetch_outgoing_linked_documents([str(uuid.uuid4())], max_docs=1)

    assert linked == ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
    assert q.limit_value == 1
    assert any("document_links.to_document_id" in ob for ob in q.order_bys)
