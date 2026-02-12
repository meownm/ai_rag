import uuid

import pytest


@pytest.mark.integration
def test_start_job_then_worker_completes(monkeypatch):
    from app.api.routes import start_source_sync
    from app.schemas.api import SourceSyncRequest
    from app.workers import ingest_worker

    class FakeRepo:
        def __init__(self, db, tenant_id):
            self.job = type(
                "Job",
                (),
                {
                    "job_id": uuid.uuid4(),
                    "job_status": "queued",
                    "tenant_id": tenant_id,
                    "job_payload_json": None,
                    "result_json": None,
                    "error_code": None,
                    "error_message": None,
                },
            )()

        def create_job(self, job_type: str, requested_by: str, payload=None):
            self.job.job_payload_json = payload
            return self.job

        def mark_job(self, *_args, **_kwargs):
            return None

    fake_repo = FakeRepo(None, uuid.uuid4())

    monkeypatch.setattr("app.api.routes.TenantRepository", lambda db, tenant: fake_repo)

    payload = SourceSyncRequest(tenant_id=fake_repo.job.tenant_id, source_types=[])
    response = start_source_sync(payload, db=object())
    assert response.job_status == "queued"

    class FakeResult:
        def mappings(self):
            return self

        def first(self):
            return {"job_id": fake_repo.job.job_id}

    class FakeQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return fake_repo.job

    class FakeDB:
        def execute(self, *_args, **_kwargs):
            return FakeResult()

        def query(self, *_args, **_kwargs):
            return FakeQuery()

        def add(self, *_args, **_kwargs):
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    class Scope:
        def __enter__(self):
            return FakeDB()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("app.workers.ingest_worker.session_scope", lambda: Scope())
    monkeypatch.setattr("app.workers.ingest_worker.ingest_sources_sync", lambda *_args, **_kwargs: {"documents": 0, "chunks": 0})

    ok = ingest_worker.process_next_job()
    assert ok is True
    assert fake_repo.job.job_status == "done"
