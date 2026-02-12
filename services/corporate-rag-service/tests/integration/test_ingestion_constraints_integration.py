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
