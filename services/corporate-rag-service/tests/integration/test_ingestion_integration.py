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
