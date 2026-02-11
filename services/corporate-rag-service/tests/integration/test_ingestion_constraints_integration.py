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
