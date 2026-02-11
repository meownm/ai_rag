import os
import uuid

import pytest


def test_postgres_fts_ranking_orders_by_rank_cd():
    pytest.importorskip("fastapi")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from app.db.repositories import TenantRepository

    create_engine = sqlalchemy.create_engine
    text = sqlalchemy.text
    sessionmaker = sqlalchemy.orm.sessionmaker
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured for Postgres integration test")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    tenant_id = "11111111-1111-1111-1111-111111111111"

    with Session() as session:
        session.execute(text("DROP TABLE IF EXISTS chunk_fts"))
        session.execute(
            text(
                """
                CREATE TABLE chunk_fts (
                    tenant_id uuid NOT NULL,
                    chunk_id uuid NOT NULL,
                    fts_doc tsvector NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY (tenant_id, chunk_id)
                )
                """
            )
        )
        a = str(uuid.uuid4())
        b = str(uuid.uuid4())
        session.execute(
            text(
                """
                INSERT INTO chunk_fts (tenant_id, chunk_id, fts_doc)
                VALUES
                    (:tenant_id, :a, to_tsvector('simple', 'vacation policy vacation policy vacation')),
                    (:tenant_id, :b, to_tsvector('simple', 'security handbook'))
                """
            ),
            {"tenant_id": tenant_id, "a": a, "b": b},
        )
        session.commit()

        scores = TenantRepository(session, tenant_id).fetch_lexical_candidate_scores("vacation policy", 5)
        ordered = list(scores.keys())
        assert ordered[0] == a
        assert scores[a] > scores[b]


def test_postgres_weighted_fts_title_term_hits_chunk_without_term():
    pytest.importorskip("fastapi")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from app.cli.fts_rebuild import rebuild_fts
    from app.db.repositories import TenantRepository

    create_engine = sqlalchemy.create_engine
    text = sqlalchemy.text
    sessionmaker = sqlalchemy.orm.sessionmaker
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured for Postgres integration test")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    tenant_id = "11111111-1111-1111-1111-111111111111"

    with Session() as session:
        session.execute(text("DROP TABLE IF EXISTS chunk_fts"))
        session.execute(text("DROP TABLE IF EXISTS chunks"))
        session.execute(text("DROP TABLE IF EXISTS documents"))
        session.execute(text("CREATE TABLE documents (document_id uuid PRIMARY KEY, tenant_id uuid NOT NULL, title text, labels jsonb, updated_date timestamptz, author text, url text)"))
        session.execute(text("CREATE TABLE chunks (chunk_id uuid PRIMARY KEY, document_id uuid NOT NULL, tenant_id uuid NOT NULL, chunk_path text, chunk_text text, token_count int, ordinal int)"))
        session.execute(text("CREATE TABLE chunk_fts (tenant_id uuid NOT NULL, chunk_id uuid NOT NULL, fts_doc tsvector NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id, chunk_id))"))
        doc = str(uuid.uuid4())
        chunk = str(uuid.uuid4())
        session.execute(text("INSERT INTO documents (document_id, tenant_id, title, labels) VALUES (:d,:t,:title, CAST(:labels AS jsonb))"), {"d": doc, "t": tenant_id, "title": "Vacation Handbook", "labels": '["hr"]'})
        session.execute(text("INSERT INTO chunks (chunk_id, document_id, tenant_id, chunk_path, chunk_text, token_count, ordinal) VALUES (:c,:d,:t,'Section','general text only',3,1)"), {"c": chunk, "d": doc, "t": tenant_id})
        session.commit()

        rebuild_fts(tenant_id=tenant_id)
        scores = TenantRepository(session, tenant_id).fetch_lexical_candidate_scores("vacation", 5)
        assert chunk in scores
        assert scores[chunk] > 0
