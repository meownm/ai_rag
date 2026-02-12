import asyncio
import uuid

import pytest

fastapi = pytest.importorskip("fastapi")
HTTPException = fastapi.HTTPException

from app.api.routes import start_source_sync
from app.schemas.api import SourceSyncRequest
from app.services.ingestion import EmbeddingIndexingError


class FakeRepo:
    def __init__(self, db, tenant_id):
        self.db = db
        self.tenant_id = tenant_id
        self.job = type("Job", (), {"job_id": uuid.uuid4(), "job_status": "queued"})()
        self.mark_calls = []

    def create_job(self, job_type: str, requested_by: str, payload=None):
        self.payload = payload
        return self.job

    def mark_job(self, job, status: str, error_code: str | None = None, error_message: str | None = None):
        self.mark_calls.append((status, error_code, error_message))
        job.job_status = status


def test_start_source_sync_returns_queued_job(monkeypatch):
    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    payload = SourceSyncRequest(tenant_id=tenant_id, source_types=["CONFLUENCE_PAGE"])
    fake_repo = FakeRepo(db=object(), tenant_id=tenant_id)

    monkeypatch.setattr("app.api.routes.TenantRepository", lambda db, tenant: fake_repo)
    response = start_source_sync(payload, db=object())

    assert response.job_status == "queued"
    assert fake_repo.payload == {"source_types": ["CONFLUENCE_PAGE"], "force_reindex": False}


class FakeUploadFile:
    def __init__(self, filename: str, payload: bytes):
        self.filename = filename
        self._payload = payload

    async def read(self):
        return self._payload


def test_upload_file_for_ingestion_uses_shared_ingestion_path(monkeypatch):
    from app.api.routes import upload_file_for_ingestion

    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    fake_repo = FakeRepo(db=object(), tenant_id=tenant_id)
    captured = {}

    def fake_ingest_sources_sync(db, tenant, source_types, **kwargs):
        captured["source_types"] = source_types
        captured["connector_registry"] = kwargs.get("connector_registry")
        return {"documents": 1, "chunks": 1, "cross_links": 0, "artifacts": 1}

    monkeypatch.setattr("app.api.routes.TenantRepository", lambda db, tenant: fake_repo)
    monkeypatch.setattr("app.api.routes.ingest_sources_sync", fake_ingest_sources_sync)

    response = asyncio.run(
        upload_file_for_ingestion(
            tenant_id=tenant_id,
            file=FakeUploadFile("a.txt", b"hello"),
            db=object(),
        )
    )

    assert response.job_status == "done"
    assert captured["source_types"] == ["FILE_UPLOAD_OBJECT"]
    assert captured["connector_registry"] is not None


def test_upload_file_for_ingestion_rejects_unsupported_extension():
    from app.api.routes import upload_file_for_ingestion

    tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            upload_file_for_ingestion(
                tenant_id=tenant_id,
                file=FakeUploadFile("a.xlsx", b"binary"),
                db=object(),
            )
        )

    assert exc.value.status_code == 400
