import uuid

from app.workers import ingest_worker


class FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class FakeQuery:
    def __init__(self, job):
        self.job = job

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.job


class FakeDB:
    def __init__(self, job):
        self.job = job

    def execute(self, *_args, **_kwargs):
        return FakeResult({"job_id": self.job.job_id})

    def query(self, *_args, **_kwargs):
        return FakeQuery(self.job)

    def add(self, *_args, **_kwargs):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


class FakeSessionContext:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, *_args):
        return False


def test_process_next_job_marks_done(monkeypatch):
    job = type(
        "Job",
        (),
        {
            "job_id": uuid.uuid4(),
            "tenant_id": uuid.uuid4(),
            "job_payload_json": {"source_types": ["CONFLUENCE_PAGE"]},
            "job_status": "queued",
            "result_json": None,
            "error_code": None,
            "error_message": None,
        },
    )()
    db = FakeDB(job)

    monkeypatch.setattr("app.workers.ingest_worker.session_scope", lambda: FakeSessionContext(db))
    monkeypatch.setattr("app.workers.ingest_worker.ingest_sources_sync", lambda *_args, **_kwargs: {"documents": 1, "chunks": 2})

    assert ingest_worker.process_next_job() is True
    assert job.job_status == "done"
    assert job.result_json == {"documents": 1, "chunks": 2}
