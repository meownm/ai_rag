import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from app.clients.embeddings_client import EmbeddingsClient
from app.cli.fts_rebuild import weighted_fts_expression
from app.services.storage import ObjectStorage, StorageConfig

Session = Any


@dataclass
class SourceItem:
    source_type: str
    external_ref: str
    title: str
    markdown: str
    url: str = ""
    author: str | None = None
    labels: list[str] = field(default_factory=list)


class ConfluenceCrawler(Protocol):
    def crawl(self, tenant_id: uuid.UUID) -> list[SourceItem]:
        ...


class FileCatalogCrawler(Protocol):
    def crawl(self, tenant_id: uuid.UUID) -> list[SourceItem]:
        ...


class StorageAdapter(Protocol):
    def put_text(self, bucket: str, key: str, text: str) -> str:
        ...


class NoopConfluenceCrawler:
    def crawl(self, tenant_id: uuid.UUID) -> list[SourceItem]:
        return []


class NoopFileCatalogCrawler:
    def crawl(self, tenant_id: uuid.UUID) -> list[SourceItem]:
        return []


def _sql(statement: str):
    import importlib
    import importlib.util

    if importlib.util.find_spec("sqlalchemy"):
        return importlib.import_module("sqlalchemy").text(statement)
    return statement


def _load_settings():
    try:
        from app.core.config import settings

        return settings
    except Exception:  # noqa: BLE001
        class _Fallback:
            S3_ENDPOINT = "http://localhost:9000"
            S3_ACCESS_KEY = "minio"
            S3_SECRET_KEY = "minio123"
            S3_REGION = "us-east-1"
            S3_SECURE = False
            S3_BUCKET_RAW = "rag-raw"
            S3_BUCKET_MARKDOWN = "rag-markdown"

        return _Fallback()


def _default_storage() -> ObjectStorage:
    cfg = _load_settings()
    return ObjectStorage(
        StorageConfig(
            endpoint=cfg.S3_ENDPOINT,
            access_key=cfg.S3_ACCESS_KEY,
            secret_key=cfg.S3_SECRET_KEY,
            region=cfg.S3_REGION,
            secure=cfg.S3_SECURE,
        )
    )


def normalize_to_markdown(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", normalized)


def extract_links(markdown: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown)


def _canonical_chunk_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _token_count(text: str) -> int:
    return len([t for t in text.split() if t])


def chunk_markdown(markdown: str, target_tokens: int = 350, hard_max_tokens: int = 520) -> list[tuple[str, str]]:
    headings: list[str] = []
    chunks: list[tuple[str, str]] = []
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        text_block = "\n".join(buf).strip()
        if text_block:
            chunks.append(("/".join(headings), text_block))
        buf.clear()

    for line in markdown.split("\n"):
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()
            headings[:] = headings[: max(level - 1, 0)]
            headings.append(title)
            continue
        buf.append(line)
        if _token_count(" ".join(buf)) >= target_tokens:
            flush()

    flush()

    final_chunks: list[tuple[str, str]] = []
    for path, chunk_text in chunks:
        words = chunk_text.split()
        if len(words) <= hard_max_tokens:
            final_chunks.append((path, chunk_text))
            continue
        step = int(hard_max_tokens * 0.85)
        for i in range(0, len(words), step):
            final_chunks.append((path, " ".join(words[i : i + hard_max_tokens])))
    return final_chunks


def stable_chunk_id(tenant_id: uuid.UUID, document_id: uuid.UUID, source_version_id: uuid.UUID, ordinal: int, chunk_text: str) -> uuid.UUID:
    canonical = _canonical_chunk_text(chunk_text)
    payload = f"{tenant_id}|{document_id}|{source_version_id}|{ordinal}|{canonical}"
    return uuid.UUID(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32])


def _upsert_source(db: Session, tenant_id: uuid.UUID, item: SourceItem) -> uuid.UUID:
    source_id = uuid.uuid4()
    db.execute(
        _sql(
            """
            INSERT INTO sources (source_id, tenant_id, source_type, external_ref, status)
            VALUES (:source_id, :tenant_id, :source_type, :external_ref, 'INDEXED')
            """
        ),
        {"source_id": source_id, "tenant_id": tenant_id, "source_type": item.source_type, "external_ref": item.external_ref},
    )
    return source_id


def _insert_source_version(db: Session, source_id: uuid.UUID, checksum: str, s3_raw_uri: str, s3_markdown_uri: str) -> uuid.UUID:
    source_version_id = uuid.uuid4()
    db.execute(
        _sql(
            """
            INSERT INTO source_versions (
                source_version_id, source_id, version_label, checksum, s3_raw_uri, s3_markdown_uri, metadata_json
            ) VALUES (:source_version_id, :source_id, :version_label, :checksum, :s3_raw_uri, :s3_markdown_uri, :metadata_json)
            """
        ),
        {
            "source_version_id": source_version_id,
            "source_id": source_id,
            "version_label": "sync",
            "checksum": checksum,
            "s3_raw_uri": s3_raw_uri,
            "s3_markdown_uri": s3_markdown_uri,
            "metadata_json": {"normalized": True},
        },
    )
    return source_version_id


def _insert_document(db: Session, tenant_id: uuid.UUID, source_id: uuid.UUID, source_version_id: uuid.UUID, item: SourceItem) -> uuid.UUID:
    document_id = uuid.uuid4()
    db.execute(
        _sql(
            """
            INSERT INTO documents (
                document_id, tenant_id, source_id, source_version_id, title, author, updated_date, url, labels
            ) VALUES (
                :document_id, :tenant_id, :source_id, :source_version_id, :title, :author, :updated_date, :url, CAST(:labels AS jsonb)
            )
            """
        ),
        {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "source_id": source_id,
            "source_version_id": source_version_id,
            "title": item.title,
            "author": item.author,
            "updated_date": datetime.now(timezone.utc),
            "url": item.url,
            "labels": json.dumps(item.labels),
        },
    )
    return document_id


def _insert_chunks(db: Session, tenant_id: uuid.UUID, document_id: uuid.UUID, source_version_id: uuid.UUID, markdown: str) -> list[uuid.UUID]:
    chunk_ids: list[uuid.UUID] = []
    for ordinal, (chunk_path, chunk_text) in enumerate(chunk_markdown(markdown)):
        chunk_id = stable_chunk_id(tenant_id, document_id, source_version_id, ordinal, chunk_text)
        chunk_ids.append(chunk_id)
        db.execute(
            _sql(
                """
                INSERT INTO chunks (chunk_id, document_id, tenant_id, chunk_path, chunk_text, token_count, ordinal)
                VALUES (:chunk_id, :document_id, :tenant_id, :chunk_path, :chunk_text, :token_count, :ordinal)
                """
            ),
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "tenant_id": tenant_id,
                "chunk_path": chunk_path,
                "chunk_text": chunk_text,
                "token_count": _token_count(chunk_text),
                "ordinal": ordinal,
            },
        )
    return chunk_ids


def _insert_links(db: Session, document_id: uuid.UUID, links: list[str]) -> int:
    created = 0
    for link_url in links:
        db.execute(
            _sql(
                """
                INSERT INTO document_links (from_document_id, to_document_id, link_url, link_type)
                VALUES (:from_document_id, NULL, :link_url, 'CONFLUENCE_PAGE_LINK')
                ON CONFLICT DO NOTHING
                """
            ),
            {"from_document_id": document_id, "link_url": link_url},
        )
        db.execute(
            _sql(
                """
                INSERT INTO cross_links (from_document_id, to_document_id, link_url, link_type)
                VALUES (:from_document_id, NULL, :link_url, 'CONFLUENCE_PAGE_LINK')
                ON CONFLICT DO NOTHING
                """
            ),
            {"from_document_id": document_id, "link_url": link_url},
        )
        created += 1
    return created



def _log_ingest_event(db: Session, tenant_id: uuid.UUID, event_type: str, payload: dict) -> None:
    db.execute(
        _sql(
            """
            INSERT INTO event_logs (event_id, tenant_id, correlation_id, event_type, log_data_mode, payload_json)
            VALUES (:event_id, :tenant_id, :correlation_id, :event_type, 'PLAIN', CAST(:payload AS jsonb))
            """
        ),
        {
            "event_id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "correlation_id": uuid.uuid4(),
            "event_type": event_type,
            "payload": json.dumps(payload),
        },
    )


def _upsert_chunk_vectors(db: Session, tenant_id: uuid.UUID, chunk_ids: list[uuid.UUID]) -> None:
    if not chunk_ids:
        return
    cfg = _load_settings()
    batch_size = int(getattr(cfg, "MAX_EMBED_BATCH_SIZE", 64))
    client = EmbeddingsClient(getattr(cfg, "EMBEDDINGS_SERVICE_URL", None), getattr(cfg, "EMBEDDINGS_TIMEOUT_SECONDS", 30))

    query_result = db.execute(
        _sql("SELECT chunk_id, chunk_text FROM chunks WHERE tenant_id = :tenant_id AND chunk_id = ANY(:chunk_ids) ORDER BY ordinal"),
        {"tenant_id": tenant_id, "chunk_ids": chunk_ids},
    )
    if not hasattr(query_result, "mappings"):
        return
    rows = query_result.mappings().all()

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        t0 = datetime.now(timezone.utc)
        try:
            for row in batch:
                _log_ingest_event(db, tenant_id, "EMBEDDINGS_REQUEST", {"chunk_id": str(row["chunk_id"]), "model": "bge-m3"})
                emb = client.embed_text(str(row["chunk_text"]), tenant_id=str(tenant_id), correlation_id=str(uuid.uuid4()))
                _log_ingest_event(db, tenant_id, "EMBEDDINGS_RESPONSE", {"chunk_id": str(row["chunk_id"]), "dimensions": len(emb)})
                db.execute(
                    _sql(
                        """
                        INSERT INTO chunk_vectors (chunk_id, tenant_id, embedding_model, embedding, embedding_dim)
                        VALUES (:chunk_id, :tenant_id, :embedding_model, CAST(:embedding AS vector), :embedding_dim)
                        ON CONFLICT (chunk_id) DO UPDATE
                        SET tenant_id = EXCLUDED.tenant_id,
                            embedding_model = EXCLUDED.embedding_model,
                            embedding = EXCLUDED.embedding,
                            embedding_dim = EXCLUDED.embedding_dim
                        """
                    ),
                    {
                        "chunk_id": row["chunk_id"],
                        "tenant_id": tenant_id,
                        "embedding_model": "bge-m3",
                        "embedding": "[" + ",".join(f"{float(x):.8f}" for x in emb) + "]",
                        "embedding_dim": len(emb),
                    },
                )
            elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
            _log_ingest_event(db, tenant_id, "PIPELINE_STAGE", {"stage": "INDEX_VECTOR", "batch_size": len(batch), "duration_ms": elapsed_ms})
        except Exception as exc:  # noqa: BLE001
            _log_ingest_event(db, tenant_id, "ERROR", {"code": "VECTOR_INDEX_ERROR", "message": str(exc), "batch_start": i})


def _upsert_fts_for_chunks(db: Session, tenant_id: uuid.UUID, chunk_ids: list[uuid.UUID]) -> None:
    if not chunk_ids:
        return
    db.execute(
        _sql(
            f"""
            INSERT INTO chunk_fts (tenant_id, chunk_id, fts_doc, updated_at)
            SELECT c.tenant_id,
                   c.chunk_id,
                   ({weighted_fts_expression()}),
                   now()
            FROM chunks c
            JOIN documents d ON d.document_id = c.document_id
            WHERE c.tenant_id = :tenant_id
              AND c.chunk_id = ANY(:chunk_ids)
            ON CONFLICT (tenant_id, chunk_id) DO UPDATE
            SET fts_doc = EXCLUDED.fts_doc,
                updated_at = now()
            """
        ),
        {"tenant_id": tenant_id, "chunk_ids": chunk_ids},
    )
    _log_ingest_event(db, tenant_id, "PIPELINE_STAGE", {"stage": "INDEX_BM25", "chunks_indexed": len(chunk_ids)})


def ingest_sources_sync(
    db: Session,
    tenant_id: uuid.UUID,
    source_types: list[str],
    confluence: ConfluenceCrawler | None = None,
    file_catalog: FileCatalogCrawler | None = None,
    storage: StorageAdapter | None = None,
) -> dict[str, int]:
    confluence = confluence or NoopConfluenceCrawler()
    file_catalog = file_catalog or NoopFileCatalogCrawler()
    storage = storage or _default_storage()

    items: list[SourceItem] = []
    if "CONFLUENCE_PAGE" in source_types or "CONFLUENCE_ATTACHMENT" in source_types:
        items.extend(confluence.crawl(tenant_id))
    if "FILE_CATALOG_OBJECT" in source_types:
        items.extend(file_catalog.crawl(tenant_id))

    docs = chunks = links = artifacts = 0
    for item in items:
        markdown = normalize_to_markdown(item.markdown)
        source_id = _upsert_source(db, tenant_id, item)

        raw_key = f"{tenant_id}/{source_id}/raw.txt"
        md_key = f"{tenant_id}/{source_id}/normalized.md"
        cfg = _load_settings()
        raw_uri = storage.put_text(cfg.S3_BUCKET_RAW, raw_key, item.markdown)
        md_uri = storage.put_text(cfg.S3_BUCKET_MARKDOWN, md_key, markdown)

        checksum = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        source_version_id = _insert_source_version(db, source_id, checksum, raw_uri, md_uri)
        document_id = _insert_document(db, tenant_id, source_id, source_version_id, item)
        chunk_ids = _insert_chunks(db, tenant_id, document_id, source_version_id, markdown)
        _upsert_chunk_vectors(db, tenant_id, chunk_ids)
        _upsert_fts_for_chunks(db, tenant_id, chunk_ids)

        links_found = extract_links(markdown)
        links += _insert_links(db, document_id, links_found)

        artifact_key = f"{tenant_id}/{source_id}/artifacts/ingestion.json"
        artifact = {
            "source_id": str(source_id),
            "source_version_id": str(source_version_id),
            "document_id": str(document_id),
            "chunks": [str(c) for c in chunk_ids],
            "links": links_found,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        storage.put_text(cfg.S3_BUCKET_MARKDOWN, artifact_key, json.dumps(artifact, ensure_ascii=False))
        artifacts += 1

        docs += 1
        chunks += len(chunk_ids)

    if hasattr(db, "commit"):
        db.commit()
    return {"documents": docs, "chunks": chunks, "cross_links": links, "artifacts": artifacts}
