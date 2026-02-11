import os
import uuid

import pytest


def test_ingest_fixture_records_and_cross_links():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    create_engine = sqlalchemy.create_engine
    text = sqlalchemy.text

    from app.services.ingestion import SourceItem, ingest_sources_sync

    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)

    class ConfluenceFixture:
        def crawl(self, tenant_id):
            return [
                SourceItem(
                    source_type="CONFLUENCE_PAGE",
                    external_ref="page:100",
                    title="Fixture",
                    markdown="# Fixture\nBody with [child](https://conf.local/page/101)",
                )
            ]

    class EmptyCatalog:
        def crawl(self, tenant_id):
            return []

    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    with Session() as session:
        result = ingest_sources_sync(session, tenant, ["CONFLUENCE_PAGE"], confluence=ConfluenceFixture(), file_catalog=EmptyCatalog())
        session.commit()
        assert result["documents"] == 1
        assert result["chunks"] >= 1

        chunk_count = session.execute(text("SELECT count(*) FROM chunks WHERE tenant_id=:tenant"), {"tenant": tenant}).scalar_one()
        cross_link_count = session.execute(text("SELECT count(*) FROM cross_links")).scalar_one()
        assert chunk_count >= 1
        assert cross_link_count >= 1


def test_ingest_is_idempotent_for_same_source_and_markdown():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    create_engine = sqlalchemy.create_engine
    text_sql = sqlalchemy.text

    from app.services.ingestion import SourceItem, ingest_sources_sync

    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_engine(db_url)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)

    class ConfluenceFixture:
        def crawl(self, tenant_id):
            return [
                SourceItem(
                    source_type="CONFLUENCE_PAGE",
                    external_ref="page:idem-1",
                    title="Fixture Idempotent",
                    markdown="# Fixture\nBody",
                )
            ]

    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    with Session() as session:
        first = ingest_sources_sync(session, tenant, ["CONFLUENCE_PAGE"], confluence=ConfluenceFixture())
        second = ingest_sources_sync(session, tenant, ["CONFLUENCE_PAGE"], confluence=ConfluenceFixture())
        session.commit()

        assert first["documents"] == 1
        assert second["documents"] == 0
        assert second["chunks"] == 0
        assert second["artifacts"] == 0

        source_count = session.execute(
            text_sql("""
            SELECT count(*)
            FROM sources
            WHERE tenant_id=:tenant
              AND source_type='CONFLUENCE_PAGE'
              AND external_ref='page:idem-1'
            """),
            {"tenant": tenant},
        ).scalar_one()
        version_count = session.execute(
            text_sql("""
            SELECT count(*)
            FROM source_versions sv
            JOIN sources s ON s.source_id = sv.source_id
            WHERE s.tenant_id=:tenant
              AND s.source_type='CONFLUENCE_PAGE'
              AND s.external_ref='page:idem-1'
            """),
            {"tenant": tenant},
        ).scalar_one()
        document_count = session.execute(
            text_sql("""
            SELECT count(*)
            FROM documents d
            JOIN sources s ON s.source_id = d.source_id
            WHERE s.tenant_id=:tenant
              AND s.source_type='CONFLUENCE_PAGE'
              AND s.external_ref='page:idem-1'
            """),
            {"tenant": tenant},
        ).scalar_one()

        assert source_count == 1
        assert version_count == 1
        assert document_count == 1
