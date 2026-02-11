import os
import uuid

import pytest



def test_postgres_fts_ranking_orders_by_rank_cd():
    pytest.importorskip("fastapi")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from app.api.routes import _fetch_lexical_candidate_scores
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

        scores, _ms = _fetch_lexical_candidate_scores(session, tenant_id, "vacation policy", 5)
        ordered = list(scores.keys())
        assert ordered[0] == a
        assert scores[a] > scores[b]
