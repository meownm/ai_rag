import os
import uuid

import pytest


def test_sources_and_source_versions_uniqueness_constraints():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = sqlalchemy.create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    text = sqlalchemy.text
    IntegrityError = sqlalchemy.exc.IntegrityError

    tenant_id = uuid.uuid4()
    source_id = uuid.uuid4()

    with Session() as session:
        session.execute(
            text("INSERT INTO tenants (tenant_id, tenant_key, display_name) VALUES (:tenant_id, :tenant_key, :display_name)"),
            {"tenant_id": tenant_id, "tenant_key": f"tenant-{tenant_id}", "display_name": "Tenant"},
        )
        session.execute(
            text(
                """
                INSERT INTO sources (source_id, tenant_id, source_type, external_ref, status)
                VALUES (:source_id, :tenant_id, 'CONFLUENCE_PAGE', 'page:dup', 'INDEXED')
                """
            ),
            {"source_id": source_id, "tenant_id": tenant_id},
        )
        session.commit()

    with Session() as session:
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    """
                    INSERT INTO sources (source_id, tenant_id, source_type, external_ref, status)
                    VALUES (:source_id, :tenant_id, 'CONFLUENCE_PAGE', 'page:dup', 'INDEXED')
                    """
                ),
                {"source_id": uuid.uuid4(), "tenant_id": tenant_id},
            )
            session.commit()
        session.rollback()

        session.execute(
            text(
                """
                INSERT INTO source_versions (
                    source_version_id, source_id, version_label, checksum, s3_raw_uri, s3_markdown_uri, metadata_json
                ) VALUES (
                    :source_version_id, :source_id, 'sync', 'same-checksum', 's3://raw/1', 's3://md/1', '{}'::jsonb
                )
                """
            ),
            {"source_version_id": uuid.uuid4(), "source_id": source_id},
        )
        session.commit()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    """
                    INSERT INTO source_versions (
                        source_version_id, source_id, version_label, checksum, s3_raw_uri, s3_markdown_uri, metadata_json
                    ) VALUES (
                        :source_version_id, :source_id, 'sync', 'same-checksum', 's3://raw/2', 's3://md/2', '{}'::jsonb
                    )
                    """
                ),
                {"source_version_id": uuid.uuid4(), "source_id": source_id},
            )
            session.commit()
        session.rollback()


def test_documents_unique_tenant_source_version_constraint():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = sqlalchemy.create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    text = sqlalchemy.text
    IntegrityError = sqlalchemy.exc.IntegrityError

    tenant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    source_version_id = uuid.uuid4()

    with Session() as session:
        session.execute(text("INSERT INTO tenants (tenant_id, tenant_key, display_name) VALUES (:tenant_id, :tenant_key, :display_name)"), {"tenant_id": tenant_id, "tenant_key": f"tenant-{tenant_id}", "display_name": "Tenant"})
        session.execute(text("INSERT INTO sources (source_id, tenant_id, source_type, external_ref, status) VALUES (:source_id, :tenant_id, 'CONFLUENCE_PAGE', :external_ref, 'INDEXED')"), {"source_id": source_id, "tenant_id": tenant_id, "external_ref": f"page:{source_id}"})
        session.execute(text("INSERT INTO source_versions (source_version_id, source_id, version_label, checksum, s3_raw_uri, s3_markdown_uri, metadata_json) VALUES (:source_version_id, :source_id, 'sync', :checksum, 's3://raw/1', 's3://md/1', '{}'::jsonb)"), {"source_version_id": source_version_id, "source_id": source_id, "checksum": f"chk-{source_version_id}"})
        session.execute(text("INSERT INTO documents (document_id, tenant_id, source_id, source_version_id, title) VALUES (:document_id, :tenant_id, :source_id, :source_version_id, 'Doc')"), {"document_id": uuid.uuid4(), "tenant_id": tenant_id, "source_id": source_id, "source_version_id": source_version_id})
        session.commit()

    with Session() as session:
        with pytest.raises(IntegrityError):
            session.execute(text("INSERT INTO documents (document_id, tenant_id, source_id, source_version_id, title) VALUES (:document_id, :tenant_id, :source_id, :source_version_id, 'Doc duplicate')"), {"document_id": uuid.uuid4(), "tenant_id": tenant_id, "source_id": source_id, "source_version_id": source_version_id})
            session.commit()
        session.rollback()


def test_document_links_requires_tenant_id_column():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = sqlalchemy.create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    text = sqlalchemy.text

    with Session() as session:
        row = session.execute(text("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'document_links' AND column_name = 'tenant_id'"))
        nullable = row.scalar_one()
        assert nullable == "NO"


def test_migration_0012_relinks_dependents_before_dedup_delete():
    migration_path = "alembic/versions/0012_documents_unique_tenant_source_version.py"
    with open(migration_path, encoding="utf-8") as f:
        body = f.read()

    assert "UPDATE chunks c" in body
    assert "UPDATE document_links dl" in body
    assert "UPDATE cross_links cl" in body
    assert "DELETE FROM documents d" in body


def test_chunk_vectors_schema_has_updated_at_default_not_null_and_composite_unique_index():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = sqlalchemy.create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    text = sqlalchemy.text

    with Session() as session:
        updated_at_col = session.execute(
            text(
                """
                SELECT is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'chunk_vectors'
                  AND column_name = 'updated_at'
                """
            )
        ).mappings().first()

        assert updated_at_col is not None
        assert updated_at_col["is_nullable"] == "NO"
        assert updated_at_col["column_default"] is not None
        assert "now()" in updated_at_col["column_default"].lower()

        unique_idx = session.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'chunk_vectors'
                  AND indexname = 'uq_chunk_vectors_tenant_chunk'
                """
            )
        ).mappings().first()

        assert unique_idx is not None
        assert "UNIQUE INDEX" in unique_idx["indexdef"]
        assert "(tenant_id, chunk_id)" in unique_idx["indexdef"]


def test_chunk_vectors_upsert_updates_updated_at_without_runtime_error():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = sqlalchemy.create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    text = sqlalchemy.text

    tenant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    source_version_id = uuid.uuid4()
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    vec0 = "[" + ",".join(["0"] * 1024) + "]"
    vec1 = "[" + ",".join(["1"] + ["0"] * 1023) + "]"

    with Session() as session:
        session.execute(text("INSERT INTO tenants (tenant_id, tenant_key, display_name) VALUES (:tenant_id, :tenant_key, :display_name)"), {"tenant_id": tenant_id, "tenant_key": f"tenant-{tenant_id}", "display_name": "Tenant"})
        session.execute(text("INSERT INTO sources (source_id, tenant_id, source_type, external_ref, status) VALUES (:source_id, :tenant_id, 'CONFLUENCE_PAGE', :external_ref, 'INDEXED')"), {"source_id": source_id, "tenant_id": tenant_id, "external_ref": f"page:{source_id}"})
        session.execute(text("INSERT INTO source_versions (source_version_id, source_id, version_label, checksum, s3_raw_uri, s3_markdown_uri, metadata_json) VALUES (:source_version_id, :source_id, 'sync', :checksum, 's3://raw/1', 's3://md/1', '{}'::jsonb)"), {"source_version_id": source_version_id, "source_id": source_id, "checksum": f"chk-{source_version_id}"})
        session.execute(text("INSERT INTO documents (document_id, tenant_id, source_id, source_version_id, title) VALUES (:document_id, :tenant_id, :source_id, :source_version_id, 'Doc')"), {"document_id": document_id, "tenant_id": tenant_id, "source_id": source_id, "source_version_id": source_version_id})
        session.execute(text("INSERT INTO chunks (chunk_id, document_id, tenant_id, chunk_path, chunk_text, token_count, ordinal) VALUES (:chunk_id, :document_id, :tenant_id, 'p', 't', 1, 0)"), {"chunk_id": chunk_id, "document_id": document_id, "tenant_id": tenant_id})

        session.execute(
            text(
                """
                INSERT INTO chunk_vectors (chunk_id, tenant_id, embedding_model, embedding, embedding_dim, embedding_input_mode)
                VALUES (:chunk_id, :tenant_id, :embedding_model, CAST(:embedding AS vector), :embedding_dim, :embedding_input_mode)
                ON CONFLICT (tenant_id, chunk_id) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding = EXCLUDED.embedding,
                    embedding_dim = EXCLUDED.embedding_dim,
                    embedding_input_mode = EXCLUDED.embedding_input_mode,
                    updated_at = now()
                """
            ),
            {"chunk_id": chunk_id, "tenant_id": tenant_id, "embedding_model": "m0", "embedding": vec0, "embedding_dim": 1024, "embedding_input_mode": "path_text_v2"},
        )

        first = session.execute(text("SELECT embedding_model, updated_at FROM chunk_vectors WHERE tenant_id = :tenant_id AND chunk_id = :chunk_id"), {"tenant_id": tenant_id, "chunk_id": chunk_id}).mappings().first()
        assert first is not None

        session.execute(
            text(
                """
                INSERT INTO chunk_vectors (chunk_id, tenant_id, embedding_model, embedding, embedding_dim, embedding_input_mode)
                VALUES (:chunk_id, :tenant_id, :embedding_model, CAST(:embedding AS vector), :embedding_dim, :embedding_input_mode)
                ON CONFLICT (tenant_id, chunk_id) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding = EXCLUDED.embedding,
                    embedding_dim = EXCLUDED.embedding_dim,
                    embedding_input_mode = EXCLUDED.embedding_input_mode,
                    updated_at = now()
                """
            ),
            {"chunk_id": chunk_id, "tenant_id": tenant_id, "embedding_model": "m1", "embedding": vec1, "embedding_dim": 1024, "embedding_input_mode": "path_text_v2"},
        )

        second = session.execute(text("SELECT embedding_model, updated_at FROM chunk_vectors WHERE tenant_id = :tenant_id AND chunk_id = :chunk_id"), {"tenant_id": tenant_id, "chunk_id": chunk_id}).mappings().first()
        assert second is not None
        assert second["embedding_model"] == "m1"
        assert second["updated_at"] >= first["updated_at"]

        session.commit()
