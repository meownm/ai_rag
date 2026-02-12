import pytest

pytest.importorskip("pydantic")

from datetime import datetime, timezone

from app.services.connectors.base import SyncContext
from app.services.connectors.s3_catalog import S3CatalogConnector


class FakeBody:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class FakeS3Client:
    def __init__(self):
        self.calls = 0

    def list_objects_v2(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {
                "IsTruncated": True,
                "NextContinuationToken": "t2",
                "Contents": [
                    {"Key": "docs/b.txt", "Size": 10, "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc), "ETag": '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"'},
                    {"Key": "docs/a.md", "Size": 10, "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc), "ETag": '"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"'},
                ],
            }
        return {
            "IsTruncated": False,
            "Contents": [
                {"Key": "docs/c.exe", "Size": 10, "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc), "ETag": '"cccccccccccccccccccccccccccccccc"'},
            ],
        }

    def get_object(self, **kwargs):
        return {"Body": FakeBody(b"# hello")}


def test_fcs_sp2_s3_descriptor_generation_pagination_sorted(monkeypatch):
    from app.services.connectors import s3_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "S3_CATALOG_BUCKET", "bucket")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_PREFIX", "docs/")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_ALLOWED_EXTENSIONS", ".txt,.md")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_MAX_OBJECT_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = S3CatalogConnector(client=FakeS3Client())
    list_result = connector.list_descriptors("t1", SyncContext(max_items_per_run=100, page_size=2, incremental_enabled=True))

    refs = [d.external_ref for d in list_result.descriptors]
    assert refs == ["s3:bucket:docs/a.md", "s3:bucket:docs/b.txt"]
    assert all(d.checksum_hint for d in list_result.descriptors)
    assert list_result.listing_complete is True


def test_fcs_sp2_s3_fetch_item_positive(monkeypatch):
    from app.services.connectors import s3_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "S3_CATALOG_BUCKET", "bucket")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_MAX_OBJECT_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = S3CatalogConnector(client=FakeS3Client())
    descriptor = connector.list_descriptors("t1", SyncContext(max_items_per_run=100, page_size=2, incremental_enabled=True)).descriptors[0]
    result = connector.fetch_item("t1", descriptor)
    assert result.error is None
    assert result.item is not None
    assert "hello" in result.item.markdown


def test_fcs_sp4_s3_fetch_negative_empty_markdown(monkeypatch):
    from app.services.connectors import s3_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "S3_CATALOG_BUCKET", "bucket")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_MAX_OBJECT_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = S3CatalogConnector(client=FakeS3Client())
    descriptor = connector.list_descriptors("t1", SyncContext(max_items_per_run=100, page_size=2, incremental_enabled=True)).descriptors[0]

    class EmptyIngestor:
        def ingest_bytes(self, *, filename: str, payload: bytes):
            from app.services.connectors.base import SourceItem

            return SourceItem(source_type="FILE_UPLOAD_OBJECT", external_ref="x", title=filename, markdown="")

    connector._ingestor = EmptyIngestor()
    result = connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "O-EMPTY-MARKDOWN"



class _CapClient:
    def list_objects_v2(self, **kwargs):
        return {
            "IsTruncated": True,
            "NextContinuationToken": "next",
            "Contents": [
                {"Key": "docs/a.md", "Size": 10, "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc), "ETag": '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"'},
                {"Key": "docs/b.md", "Size": 10, "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc), "ETag": '"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"'},
            ],
        }


def test_fcs_sp1_s3_listing_complete_false_on_cap(monkeypatch):
    from app.services.connectors import s3_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "S3_CATALOG_BUCKET", "bucket")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_PREFIX", "docs/")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_ALLOWED_EXTENSIONS", ".md")
    monkeypatch.setattr(fake_settings, "S3_CATALOG_MAX_OBJECT_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = S3CatalogConnector(client=_CapClient())
    result = connector.list_descriptors("t1", SyncContext(max_items_per_run=1, page_size=2, incremental_enabled=True))

    assert len(result.descriptors) == 1
    assert result.listing_complete is False
