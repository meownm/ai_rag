from __future__ import annotations

import json
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

    @staticmethod
    def _to_vector_literal(query_embedding: list[float]) -> str:
        return "[" + ",".join(f"{float(x):.8f}" for x in query_embedding) + "]"

    def fetch_vector_candidates_by_similarity(self, query_embedding: list[float], top_n: int) -> list[dict]:
        vector_literal = self._to_vector_literal(query_embedding)
        rows = self.db.execute(
            text(
                """
                SELECT cv.chunk_id::text AS chunk_id,
                       (cv.embedding <-> CAST(:qvec AS vector)) AS distance,
                       (1.0 / (1.0 + (cv.embedding <-> CAST(:qvec AS vector)))) AS vec_score
                FROM chunk_vectors cv
                JOIN chunks c ON c.chunk_id = cv.chunk_id
                JOIN documents d ON d.document_id = c.document_id
                WHERE cv.tenant_id = CAST(:tenant_id AS uuid)
                  AND c.tenant_id = CAST(:tenant_id AS uuid)
                  AND d.tenant_id = CAST(:tenant_id AS uuid)
                ORDER BY cv.embedding <-> CAST(:qvec AS vector)
                LIMIT :limit_n
                """
            ),
            {"tenant_id": self.tenant_id, "qvec": vector_literal, "limit_n": top_n},
        ).mappings().all()
        return [
            {
                "chunk_id": row["chunk_id"],
                "distance": float(row["distance"] or 0.0),
                "vec_score": float(row["vec_score"] or 0.0),
            }
            for row in rows
        ]

    def fetch_vector_candidates_by_ordinal(self, top_n: int) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT cv.chunk_id::text AS chunk_id,
                       0.0 AS distance,
                       0.0 AS vec_score
                FROM chunk_vectors cv
                JOIN chunks c ON c.chunk_id = cv.chunk_id
                JOIN documents d ON d.document_id = c.document_id
                WHERE cv.tenant_id = CAST(:tenant_id AS uuid)
                  AND c.tenant_id = CAST(:tenant_id AS uuid)
                  AND d.tenant_id = CAST(:tenant_id AS uuid)
                ORDER BY c.ordinal ASC
                LIMIT :limit_n
                """
            ),
            {"tenant_id": self.tenant_id, "limit_n": top_n},
        ).mappings().all()
        return [
            {
                "chunk_id": row["chunk_id"],
                "distance": float(row["distance"] or 0.0),
                "vec_score": float(row["vec_score"] or 0.0),
            }
            for row in rows
        ]

    def fetch_vector_candidates(self, query_embedding: list[float], top_n: int, use_similarity: bool = False) -> list[dict]:
        if use_similarity:
            return self.fetch_vector_candidates_by_similarity(query_embedding, top_n)
        return self.fetch_vector_candidates_by_ordinal(top_n)

    def hydrate_candidates(self, chunk_ids: set[str], lexical_scores: dict[str, float], vector_scores: dict[str, float] | None = None) -> list[dict]:
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
        vector_scores = vector_scores or {}
        return [
            self._row_to_candidate(
                chunk,
                document,
                vector,
                lexical_scores.get(str(chunk.chunk_id), 0.0),
                vector_scores.get(str(chunk.chunk_id), 0.0),
            )
            for chunk, document, vector in rows
        ]

    def fetch_neighbors(self, base_chunks: list[dict], cap: int, window: int = 1) -> list[dict]:
        if not base_chunks or cap <= 0 or window < 1:
            return []
        by_doc: dict[str, set[int]] = {}
        base_chunks_by_doc: dict[str, list[dict]] = {}
        for c in base_chunks:
            doc_id = str(c["document_id"])
            ordinal = int(c.get("ordinal", 0))
            window_ordinals = range(ordinal - window, ordinal + window + 1)
            by_doc.setdefault(doc_id, set()).update(window_ordinals)
            base_chunks_by_doc.setdefault(doc_id, []).append(c)

        neighbors: list[dict] = []
        seen = {str(c["chunk_id"]) for c in base_chunks}
        for doc_id, ordinals in by_doc.items():
            if len(neighbors) >= cap:
                break
            rows = (
                self.db.query(Chunks, Documents, ChunkVectors)
                .join(Documents, Documents.document_id == Chunks.document_id)
                .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
                .filter(Chunks.tenant_id == self.tenant_id)
                .filter(Documents.tenant_id == self.tenant_id)
                .filter(ChunkVectors.tenant_id == self.tenant_id)
                .filter(Chunks.document_id == doc_id)
                .filter(Chunks.ordinal.in_(ordinals))
                .order_by(Chunks.ordinal.asc())
                .all()
            )
            for row in rows:
                chunk, document, vector = row
                chunk_id = str(chunk.chunk_id)
                if chunk_id in seen:
                    continue
                seen.add(chunk_id)

                base_matches = base_chunks_by_doc.get(doc_id, [])
                if not base_matches:
                    continue
                base = min(base_matches, key=lambda b: abs(int(b.get("ordinal", 0)) - int(chunk.ordinal)))
                base_score = float(base.get("final_score", 0.0))
                candidate = self._row_to_candidate(chunk, document, vector, 0.0, max(0.0, float(base.get("vec_score", 0.0)) * 0.95))
                candidate["rerank_score"] = float(base.get("rerank_score", 0.0)) * 0.95
                candidate["final_score"] = max(0.0, base_score * 0.92)
                candidate["boosts_applied"] = [
                    *base.get("boosts_applied", []),
                    {"name": "neighbor_expansion", "value": -0.08, "reason": f"expanded_from:{base['chunk_id']}"},
                ]
                candidate["added_by_neighbor"] = True
                candidate["base_chunk_id"] = str(base["chunk_id"])
                neighbors.append(candidate)
                if len(neighbors) >= cap:
                    break
        return neighbors

    @staticmethod
    def _labels_to_list(labels: object) -> list[str]:
        if labels is None:
            return []
        if isinstance(labels, list):
            return [str(x) for x in labels]
        if isinstance(labels, str):
            try:
                parsed = json.loads(labels)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except json.JSONDecodeError:
                return [labels]
        return [str(labels)]

    @classmethod
    def _row_to_candidate(cls, chunk: Chunks, document: Documents, vector: ChunkVectors, lex_score: float, vec_score: float = 0.0) -> dict:
        return {
            "chunk_id": str(chunk.chunk_id),
            "document_id": document.document_id,
            "chunk_text": chunk.chunk_text,
            "title": document.title,
            "url": document.url or "",
            "heading_path": chunk.chunk_path.split("/") if chunk.chunk_path else [],
            "labels": cls._labels_to_list(document.labels),
            "author": document.author,
            "updated_at": document.updated_date.isoformat() if document.updated_date else "",
            "tenant_id": str(chunk.tenant_id),
            "ordinal": int(chunk.ordinal),
            "embedding": list(vector.embedding),
            "lex_score": float(lex_score),
            "vec_score": float(vec_score),
        }
