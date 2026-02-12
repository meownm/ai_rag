from __future__ import annotations

import logging
import time
from contextlib import contextmanager

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.models import IngestJobs
from app.services.ingestion import EmbeddingIndexingError, ingest_sources_sync

LOGGER = logging.getLogger(__name__)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def process_next_job() -> bool:
    with session_scope() as db:
        row = db.execute(
            text(
                """
                SELECT job_id
                FROM ingest_jobs
                WHERE job_status = 'queued'
                ORDER BY started_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            )
        ).mappings().first()
        if not row:
            db.rollback()
            return False

        job = db.query(IngestJobs).filter(IngestJobs.job_id == row["job_id"]).first()
        if not job:
            db.rollback()
            return False

        job.job_status = "processing"
        db.add(job)
        db.commit()

        try:
            payload = job.job_payload_json or {}
            source_types = payload.get("source_types") or []
            result = ingest_sources_sync(db, job.tenant_id, source_types)
            job.job_status = "done"
            job.result_json = result
            job.error_code = None
            job.error_message = None
        except EmbeddingIndexingError as exc:
            job.job_status = "error"
            job.error_code = "S-EMB-INDEX-FAILED"
            job.error_message = str(exc)
        except Exception as exc:  # noqa: BLE001
            job.job_status = "error"
            job.error_code = "SOURCE_FETCH_FAILED"
            job.error_message = str(exc)

        db.add(job)
        db.commit()
        LOGGER.info("ingest_worker_processed", extra={"job_id": str(job.job_id), "job_status": job.job_status})
        return True


def run_forever(poll_interval_seconds: float = 1.0) -> None:
    while True:
        has_work = process_next_job()
        if not has_work:
            time.sleep(max(0.1, poll_interval_seconds))


if __name__ == "__main__":
    run_forever()
