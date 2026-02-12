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
