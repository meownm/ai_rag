from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.logging import log_event
from app.db.errors import DatabaseOperationError

from app.models.models import (
    Chunks,
    ChunkVectors,
    ConversationSummaries,
    Conversations,
    ConversationTurns,
    Documents,
    DocumentLinks,
    EventLogs,
    IngestJobs,
    QueryResolutions,
    RetrievalTraceItems,
)


def _map_db_error(exc: Exception) -> tuple[str, str | None, bool]:
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
    code_map = {
        "23505": ("unique_violation", False),
        "23503": ("foreign_key_violation", False),
        "40P01": ("deadlock_detected", True),
    }
    error_code, retryable = code_map.get(str(sqlstate), ("database_error", False))
    return error_code, sqlstate, retryable


def _commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        error_code, sqlstate, retryable = _map_db_error(exc)
        log_event(
            "error.occurred",
            level=40,
            payload={
                "error_code": error_code,
                "error_category": "database",
                "sqlstate": sqlstate,
                "retryable": retryable,
            },
            plane="data",
        )
        raise DatabaseOperationError(error_code=error_code, sqlstate=sqlstate, retryable=retryable) from exc



class TenantRepository:
    """Tenant-safe access helpers for critical tables."""

    def __init__(self, db: Session, tenant_id: str | uuid.UUID):
        self.db = db
        self.tenant_id = str(tenant_id)

    def create_job(self, job_type: str, requested_by: str, payload: dict | None = None) -> IngestJobs:
        job = IngestJobs(
            tenant_id=self.tenant_id,
            job_type=job_type,
            job_status="queued",
            requested_by=requested_by,
            job_payload_json=payload,
        )
        self.db.add(job)
        _commit_or_raise(self.db)
        self.db.refresh(job)
        return job

    def get_job(self, job_id: uuid.UUID) -> IngestJobs | None:
        return (
            self.db.query(IngestJobs)
            .filter(IngestJobs.tenant_id == self.tenant_id)
            .filter(IngestJobs.job_id == job_id)
            .first()
        )

    def mark_job(
        self,
        job: IngestJobs,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        result_payload: dict | None = None,
    ) -> None:
        job.job_status = status
        job.error_code = error_code
        job.error_message = error_message
        if result_payload is not None:
            job.result_json = result_payload
        if status in {"done", "error", "canceled", "expired"}:
            job.finished_at = datetime.now(timezone.utc)
        self.db.add(job)
        _commit_or_raise(self.db)

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
        _commit_or_raise(self.db)

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

    def fetch_chunk_by_id(self, chunk_id: str) -> dict | None:
        row = (
            self.db.query(Chunks, Documents, ChunkVectors)
            .join(Documents, Documents.document_id == Chunks.document_id)
            .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
            .filter(Chunks.tenant_id == self.tenant_id)
            .filter(Documents.tenant_id == self.tenant_id)
            .filter(ChunkVectors.tenant_id == self.tenant_id)
            .filter(Chunks.chunk_id == chunk_id)
            .first()
        )
        if row is None:
            return None
        chunk, document, vector = row
        return self._row_to_candidate(chunk, document, vector, 0.0, 0.0)

    def fetch_document_neighbors(self, document_id: str, anchor_chunk_id: str, window: int = 1) -> list[dict]:
        if window < 0:
            return []
        anchor = (
            self.db.query(Chunks)
            .filter(Chunks.tenant_id == self.tenant_id)
            .filter(Chunks.document_id == document_id)
            .filter(Chunks.chunk_id == anchor_chunk_id)
            .first()
        )
        if anchor is None:
            return []

        min_ord = int(anchor.ordinal) - int(window)
        max_ord = int(anchor.ordinal) + int(window)
        rows = (
            self.db.query(Chunks, Documents, ChunkVectors)
            .join(Documents, Documents.document_id == Chunks.document_id)
            .join(ChunkVectors, ChunkVectors.chunk_id == Chunks.chunk_id)
            .filter(Chunks.tenant_id == self.tenant_id)
            .filter(Documents.tenant_id == self.tenant_id)
            .filter(ChunkVectors.tenant_id == self.tenant_id)
            .filter(Chunks.document_id == document_id)
            .filter(Chunks.ordinal >= min_ord)
            .filter(Chunks.ordinal <= max_ord)
            .order_by(Chunks.ordinal.asc(), Chunks.chunk_id.asc())
            .all()
        )
        return [self._row_to_candidate(chunk, document, vector, 0.0, 0.0) for chunk, document, vector in rows]

    def fetch_outgoing_linked_documents(self, document_ids: list[str], max_docs: int) -> list[str]:
        if not document_ids or max_docs <= 0:
            return []
        rows = (
            self.db.query(DocumentLinks.to_document_id)
            .join(Documents, Documents.document_id == DocumentLinks.to_document_id)
            .filter(DocumentLinks.from_document_id.in_(document_ids))
            .filter(DocumentLinks.to_document_id.isnot(None))
            .filter(Documents.tenant_id == self.tenant_id)
            .order_by(DocumentLinks.to_document_id.asc())
            .limit(max_docs)
            .all()
        )
        return [str(row[0]) for row in rows if row[0] is not None]

    def fetch_top_chunks_for_document(self, document_id: str, query_embedding: list[float], limit_n: int = 2) -> list[dict]:
        if limit_n <= 0:
            return []
        vector_literal = self._to_vector_literal(query_embedding)
        rows = self.db.execute(
            text(
                """
                SELECT c.chunk_id,
                       c.document_id,
                       c.chunk_text,
                       c.chunk_path,
                       c.ordinal,
                       c.token_count,
                       d.title,
                       d.author,
                       d.url,
                       d.labels,
                       d.updated_date,
                       cv.embedding,
                       (1.0 / (1.0 + (cv.embedding <-> CAST(:qvec AS vector)))) AS vec_score
                FROM chunks c
                JOIN documents d ON d.document_id = c.document_id
                JOIN chunk_vectors cv ON cv.chunk_id = c.chunk_id
                WHERE c.tenant_id = CAST(:tenant_id AS uuid)
                  AND d.tenant_id = CAST(:tenant_id AS uuid)
                  AND cv.tenant_id = CAST(:tenant_id AS uuid)
                  AND c.document_id = CAST(:document_id AS uuid)
                ORDER BY cv.embedding <-> CAST(:qvec AS vector), c.ordinal ASC, c.chunk_id ASC
                LIMIT :limit_n
                """
            ),
            {
                "tenant_id": self.tenant_id,
                "document_id": document_id,
                "qvec": vector_literal,
                "limit_n": limit_n,
            },
        ).mappings().all()
        items: list[dict] = []
        for row in rows:
            labels = self._labels_to_list(row["labels"])
            items.append(
                {
                    "chunk_id": str(row["chunk_id"]),
                    "document_id": row["document_id"],
                    "chunk_text": row["chunk_text"],
                    "title": row["title"],
                    "url": row["url"] or "",
                    "heading_path": row["chunk_path"].split("/") if row["chunk_path"] else [],
                    "labels": labels,
                    "author": row["author"],
                    "updated_at": row["updated_date"].isoformat() if row["updated_date"] else "",
                    "tenant_id": self.tenant_id,
                    "ordinal": int(row["ordinal"]),
                    "token_count": int(row["token_count"] or 0),
                    "embedding": list(row["embedding"]),
                    "lex_score": 0.0,
                    "vec_score": float(row["vec_score"] or 0.0),
                    "final_score": float(row["vec_score"] or 0.0),
                }
            )
        return items

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


class ConversationRepository:
    """Tenant-scoped conversation persistence helpers."""

    def __init__(self, db: Session, tenant_id: str | uuid.UUID):
        self.db = db
        self.tenant_id = str(tenant_id)

    def get_conversation(self, conversation_id: uuid.UUID) -> Conversations | None:
        return (
            self.db.query(Conversations)
            .filter(Conversations.tenant_id == self.tenant_id)
            .filter(Conversations.conversation_id == conversation_id)
            .first()
        )

    def create_conversation(self, conversation_id: uuid.UUID, status: str = "active") -> Conversations:
        conversation = Conversations(conversation_id=conversation_id, tenant_id=self.tenant_id, status=status)
        self.db.add(conversation)
        _commit_or_raise(self.db)
        self.db.refresh(conversation)
        return conversation

    def mark_conversation_archived(self, conversation: Conversations) -> None:
        conversation.status = "archived"
        conversation.last_active_at = datetime.now(timezone.utc)
        self.db.add(conversation)
        _commit_or_raise(self.db)

    def touch_conversation(self, conversation: Conversations) -> None:
        conversation.last_active_at = datetime.now(timezone.utc)
        self.db.add(conversation)
        _commit_or_raise(self.db)

    def get_next_turn_index(self, conversation_id: uuid.UUID) -> int:
        turn = (
            self.db.query(ConversationTurns)
            .filter(ConversationTurns.tenant_id == self.tenant_id)
            .filter(ConversationTurns.conversation_id == conversation_id)
            .order_by(ConversationTurns.turn_index.desc())
            .first()
        )
        if turn is None:
            return 1
        return int(turn.turn_index) + 1

    def create_turn(
        self,
        conversation_id: uuid.UUID,
        role: str,
        text: str,
        meta: dict | None = None,
        turn_index: int | None = None,
    ) -> ConversationTurns:
        resolved_turn_index = turn_index if turn_index is not None else self.get_next_turn_index(conversation_id)
        turn = ConversationTurns(
            conversation_id=conversation_id,
            tenant_id=self.tenant_id,
            turn_index=resolved_turn_index,
            role=role,
            text=text,
            meta=meta,
        )
        self.db.add(turn)
        _commit_or_raise(self.db)
        self.db.refresh(turn)
        return turn

    def create_query_resolution(
        self,
        *,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        resolved_query_text: str,
        rewrite_strategy: str,
        rewrite_inputs: dict | None,
        rewrite_confidence: float | None,
        topic_shift_detected: bool,
        needs_clarification: bool,
        clarification_question: str | None,
    ) -> QueryResolutions:
        resolution = QueryResolutions(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            resolved_query_text=resolved_query_text,
            rewrite_strategy=rewrite_strategy,
            rewrite_inputs=rewrite_inputs,
            rewrite_confidence=rewrite_confidence,
            topic_shift_detected=topic_shift_detected,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
        )
        self.db.add(resolution)
        _commit_or_raise(self.db)
        self.db.refresh(resolution)
        return resolution

    def create_retrieval_trace_items(self, items: list[dict]) -> int:
        created = 0
        for item in items:
            trace_item = RetrievalTraceItems(
                tenant_id=self.tenant_id,
                conversation_id=item["conversation_id"],
                turn_id=item["turn_id"],
                document_id=item["document_id"],
                chunk_id=item["chunk_id"],
                ordinal=item["ordinal"],
                score_lex_raw=item.get("score_lex_raw"),
                score_vec_raw=item.get("score_vec_raw"),
                score_rerank_raw=item.get("score_rerank_raw"),
                score_final=item.get("score_final"),
                used_in_context=bool(item.get("used_in_context", False)),
                used_in_answer=bool(item.get("used_in_answer", False)),
                citation_rank=item.get("citation_rank"),
            )
            self.db.add(trace_item)
            created += 1
        if created > 0:
            _commit_or_raise(self.db)
        return created

    def list_turns(self, conversation_id: uuid.UUID, limit: int = 50) -> list[ConversationTurns]:
        return (
            self.db.query(ConversationTurns)
            .filter(ConversationTurns.tenant_id == self.tenant_id)
            .filter(ConversationTurns.conversation_id == conversation_id)
            .order_by(ConversationTurns.turn_index.desc())
            .limit(limit)
            .all()
        )

    def get_latest_query_resolution(self, conversation_id: uuid.UUID) -> QueryResolutions | None:
        return (
            self.db.query(QueryResolutions)
            .filter(QueryResolutions.tenant_id == self.tenant_id)
            .filter(QueryResolutions.conversation_id == conversation_id)
            .order_by(QueryResolutions.created_at.desc())
            .first()
        )

    def count_recent_consecutive_clarifications(self, conversation_id: uuid.UUID, max_scan: int = 10) -> int:
        rows = (
            self.db.query(QueryResolutions)
            .filter(QueryResolutions.tenant_id == self.tenant_id)
            .filter(QueryResolutions.conversation_id == conversation_id)
            .order_by(QueryResolutions.created_at.desc())
            .limit(max_scan)
            .all()
        )
        count = 0
        for row in rows:
            if bool(row.needs_clarification):
                count += 1
                continue
            break
        return count

    def list_query_resolutions(self, conversation_id: uuid.UUID, limit: int = 50) -> list[QueryResolutions]:
        return (
            self.db.query(QueryResolutions)
            .filter(QueryResolutions.tenant_id == self.tenant_id)
            .filter(QueryResolutions.conversation_id == conversation_id)
            .order_by(QueryResolutions.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_retrieval_trace_items(self, conversation_id: uuid.UUID, turn_id: uuid.UUID | None = None, limit: int = 100) -> list[RetrievalTraceItems]:
        query = (
            self.db.query(RetrievalTraceItems)
            .filter(RetrievalTraceItems.tenant_id == self.tenant_id)
            .filter(RetrievalTraceItems.conversation_id == conversation_id)
        )
        if turn_id is not None:
            query = query.filter(RetrievalTraceItems.turn_id == turn_id)
        return query.order_by(RetrievalTraceItems.created_at.desc()).limit(limit).all()

    def get_latest_summary(self, conversation_id: uuid.UUID) -> ConversationSummaries | None:
        return (
            self.db.query(ConversationSummaries)
            .filter(ConversationSummaries.tenant_id == self.tenant_id)
            .filter(ConversationSummaries.conversation_id == conversation_id)
            .order_by(ConversationSummaries.summary_version.desc())
            .first()
        )

    def create_summary(
        self,
        *,
        conversation_id: uuid.UUID,
        summary_text: str,
        covers_turn_index_to: int,
    ) -> ConversationSummaries:
        latest = self.get_latest_summary(conversation_id)
        next_version = 1 if latest is None else int(latest.summary_version) + 1
        summary = ConversationSummaries(
            tenant_id=self.tenant_id,
            conversation_id=conversation_id,
            summary_version=next_version,
            summary_text=summary_text,
            covers_turn_index_to=covers_turn_index_to,
        )
        self.db.add(summary)
        _commit_or_raise(self.db)
        self.db.refresh(summary)
        return summary

    def list_summaries(self, conversation_id: uuid.UUID, limit: int = 20) -> list[ConversationSummaries]:
        return (
            self.db.query(ConversationSummaries)
            .filter(ConversationSummaries.tenant_id == self.tenant_id)
            .filter(ConversationSummaries.conversation_id == conversation_id)
            .order_by(ConversationSummaries.summary_version.desc())
            .limit(limit)
            .all()
        )
