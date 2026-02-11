from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Chunks, ChunkVectors, Documents, EventLogs, IngestJobs


class TenantRepository:
    """Tenant-safe access helpers for critical tables."""

    def __init__(self, db: Session, tenant_id: str | uuid.UUID):
        self.db = db
        self.tenant_id = str(tenant_id)

    def create_job(self, job_type: str, requested_by: str) -> IngestJobs:
        job = IngestJobs(tenant_id=self.tenant_id, job_type=job_type, job_status="processing", requested_by=requested_by)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: uuid.UUID) -> IngestJobs | None:
        return (
            self.db.query(IngestJobs)
            .filter(IngestJobs.tenant_id == self.tenant_id)
            .filter(IngestJobs.job_id == job_id)
            .first()
        )

    def mark_job(self, job: IngestJobs, status: str, error_code: str | None = None, error_message: str | None = None) -> None:
        job.job_status = status
        job.error_code = error_code
        job.error_message = error_message
        if status in {"done", "error", "canceled", "expired"}:
            job.finished_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.commit()

    def log_event(self, correlation_id: str, event_type: str, payload: dict, duration_ms: int | None = None) -> None:
        self.db.add(
            EventLogs(
                tenant_id=self.tenant_id,
                correlation_id=correlation_id,
                event_type=event_type,
                payload_json=payload,
                duration_ms=duration_ms,
            )
        )
        self.db.commit()

    def fetch_lexical_candidate_scores(self, query: str, top_n: int) -> dict[str, float]:
        rows = self.db.execute(
            text(
                """
                SELECT cf.chunk_id::text AS chunk_id,
                       ts_rank_cd(cf.fts_doc, plainto_tsquery('simple', :query_text)) AS lex_score
                FROM chunk_fts cf
                WHERE cf.tenant_id = CAST(:tenant_id AS uuid)
                  AND cf.fts_doc @@ plainto_tsquery('simple', :query_text)
                ORDER BY lex_score DESC
                LIMIT :limit_n
                """
            ),
            {"tenant_id": self.tenant_id, "query_text": query, "limit_n": top_n},
        ).mappings().all()
        return {row["chunk_id"]: float(row["lex_score"] or 0.0) for row in rows}

    def fetch_vector_candidates(self, top_n: int) -> list[dict]:
        rows = (
            self.db.query(Chunks, Documents, ChunkVectors)
            .join(Documents, Documents.document_id == Chunks.document_id)
            .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
            .filter(Chunks.tenant_id == self.tenant_id)
            .filter(Documents.tenant_id == self.tenant_id)
            .filter(ChunkVectors.tenant_id == self.tenant_id)
            .order_by(Chunks.ordinal.asc())
            .limit(top_n)
            .all()
        )
        return [self._row_to_candidate(chunk, document, vector, 0.0) for chunk, document, vector in rows]

    def hydrate_candidates(self, chunk_ids: set[str], lexical_scores: dict[str, float]) -> list[dict]:
        if not chunk_ids:
            return []
        rows = (
            self.db.query(Chunks, Documents, ChunkVectors)
            .join(Documents, Documents.document_id == Chunks.document_id)
            .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
            .filter(Chunks.tenant_id == self.tenant_id)
            .filter(Documents.tenant_id == self.tenant_id)
            .filter(ChunkVectors.tenant_id == self.tenant_id)
            .filter(Chunks.chunk_id.in_(chunk_ids))
            .all()
        )
        return [self._row_to_candidate(chunk, document, vector, lexical_scores.get(str(chunk.chunk_id), 0.0)) for chunk, document, vector in rows]

    @staticmethod
    def _row_to_candidate(chunk: Chunks, document: Documents, vector: ChunkVectors, lex_score: float) -> dict:
        return {
            "chunk_id": str(chunk.chunk_id),
            "document_id": document.document_id,
            "chunk_text": chunk.chunk_text,
            "title": document.title,
            "url": document.url or "",
            "heading_path": chunk.chunk_path.split("/") if chunk.chunk_path else [],
            "labels": document.labels or [],
            "author": document.author,
            "updated_at": document.updated_date.isoformat() if document.updated_date else "",
            "tenant_id": str(chunk.tenant_id),
            "embedding": list(vector.embedding),
            "lex_score": lex_score,
        }
