"""Ingestion pipeline for connector-provided markdown sources."""

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from app.clients.embeddings_client import EmbeddingsClient
from app.cli.fts_rebuild import weighted_fts_expression
from app.services.storage import ObjectStorage, StorageConfig
from app.services.tokenizer import token_count

Session = Any
LOGGER = logging.getLogger(__name__)


class EmbeddingIndexingError(Exception):
    pass


from types import SimpleNamespace

try:
    from app.core.config import settings
except Exception:  # noqa: BLE001
    settings = SimpleNamespace(
        S3_ENDPOINT="http://localhost:9000",
        S3_ACCESS_KEY="minio",
        S3_SECRET_KEY="minio123",
        S3_REGION="us-east-1",
        S3_SECURE=False,
        S3_BUCKET_RAW="rag-raw",
        S3_BUCKET_MARKDOWN="rag-markdown",
        EMBEDDINGS_SERVICE_URL="http://localhost:8200",
        EMBEDDINGS_TIMEOUT_SECONDS=30,
        EMBEDDINGS_BATCH_SIZE=64,
        EMBEDDINGS_RETRY_ATTEMPTS=3,
        EMBEDDINGS_DEFAULT_MODEL_ID="bge-m3",
        CHUNK_TARGET_TOKENS=650,
        CHUNK_MAX_TOKENS=900,
        CHUNK_MIN_TOKENS=120,
        CHUNK_OVERLAP_TOKENS=80,
        CONNECTOR_REGISTRY_ENABLED=True,
        CONNECTOR_SYNC_MAX_ITEMS_PER_RUN=5000,
        CONNECTOR_SYNC_PAGE_SIZE=100,
        CONNECTOR_INCREMENTAL_ENABLED=True,
    )

from app.db.repositories.source_sync_state import SourceSyncStateRepository
from app.services.connectors import register_default_connectors
from app.services.connectors.base import SourceDescriptor, SourceItem, SyncContext
from app.services.connectors.registry import ConnectorRegistryError


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
    return settings


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


def normalize_to_markdown(content: str, *, normalize_inline_whitespace: bool = True) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    out_lines: list[str] = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            out_lines.append(line)
            in_code_block = not in_code_block
            continue

        if in_code_block:
            out_lines.append(line)
            continue

        if not line:
            out_lines.append(line)
            continue

        match = re.match(r"^[ \t]*", line)
        leading = match.group(0) if match else ""
        body = line[len(leading) :]
        if "|" in body and body.count("|") >= 2:
            out_lines.append(f"{leading}{body.rstrip()}")
            continue

        normalized_body = re.sub(r"[ \t]+", " ", body).rstrip() if normalize_inline_whitespace else body.rstrip()
        out_lines.append(f"{leading}{normalized_body}")

    return "\n".join(out_lines)



def extract_links(markdown: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown)


def _canonical_chunk_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _token_count(text: str) -> int:
    cfg = _load_settings()
    return token_count(text, estimator=getattr(cfg, "TOKEN_ESTIMATOR", "split"))


def _is_table_separator_line(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    parts = [part.strip() for part in stripped.strip("|").split("|")]
    if not parts:
        return False
    return all(bool(re.fullmatch(r":?-{3,}:?", part)) for part in parts if part)


def _is_pipe_heavy_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.count("|") >= 2


def _is_table_header_line(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("```"):
        return False
    if stripped.count("|") < 2:
        return False
    parts = [part.strip() for part in stripped.strip("|").split("|")]
    if not parts or not any(parts):
        return False
    return not _is_table_separator_line(line)


def _line_type(line: str, in_code_block: bool) -> str:
    stripped = line.strip()
    if stripped.startswith("```"):
        return "code"
    if in_code_block:
        return "code"
    if not stripped:
        return "blank"
    if re.match(r"^#{1,6}\s", stripped):
        return "heading"
    if re.match(r"^>\s?", stripped):
        return "quote"
    if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
        return "list"
    return "paragraph"


def _parse_markdown_blocks(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.splitlines(keepends=True)
    line_starts: list[int] = []
    running = 0
    for raw_line in lines:
        line_starts.append(running)
        running += len(raw_line)

    blocks: list[dict[str, Any]] = []
    headings_path: list[str] = []
    in_code_block = False

    current_type: str | None = None
    current_lines: list[str] = []
    current_start = 0
    current_path: list[str] = []
    offset = 0

    def flush(end_pos: int) -> None:
        nonlocal current_type, current_lines, current_start, current_path
        if not current_type or not current_lines:
            current_type = None
            current_lines = []
            return
        text = "".join(current_lines)
        if text:
            blocks.append(
                {
                    "type": current_type,
                    "text": text,
                    "char_start": current_start,
                    "char_end": end_pos,
                    "token_estimate": _token_count(text),
                    "headings_path": list(current_path),
                }
            )
        current_type = None
        current_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        line_start = line_starts[i]
        offset = line_start + len(line)
        line_t = _line_type(line, in_code_block)

        if line.strip().startswith("```"):
            if in_code_block and current_type == "code":
                current_lines.append(line)
                flush(offset)
                in_code_block = False
                i += 1
                continue
            in_code_block = True
            if current_type not in (None, "code"):
                flush(line_start)
            if current_type is None:
                current_type = "code"
                current_start = line_start
                current_path = list(headings_path)
            current_lines.append(line)
            i += 1
            continue

        if line_t == "heading":
            flush(line_start)
            stripped = line.lstrip().rstrip("\r\n")
            heading_level = len(stripped) - len(stripped.lstrip("#"))
            heading_title = stripped[heading_level:].strip()
            headings_path[:] = headings_path[: max(heading_level - 1, 0)]
            headings_path.append(heading_title)
            i += 1
            continue

        if not in_code_block and (i + 1) < len(lines) and _is_table_header_line(line) and _is_table_separator_line(lines[i + 1]):
            j = i + 2
            while j < len(lines) and _is_pipe_heavy_line(lines[j]) and not lines[j].strip().startswith("```"):
                j += 1

            if j - i >= 2:
                flush(line_start)
                current_type = "table"
                current_start = line_start
                current_path = list(headings_path)
                current_lines = lines[i:j]
                flush(line_starts[j] if j < len(lines) else len(markdown))
                i = j
                continue

        if line_t == "blank":
            flush(line_start)
            i += 1
            continue

        if current_type is None:
            current_type = line_t
            current_start = line_start
            current_path = list(headings_path)
            current_lines = [line]
            i += 1
            continue

        if current_type == line_t and current_path == headings_path:
            current_lines.append(line)
            i += 1
            continue

        flush(line_start)
        current_type = line_t
        current_start = line_start
        current_path = list(headings_path)
        current_lines = [line]
        i += 1

    flush(len(markdown))
    return blocks


def _split_large_block(
    *,
    text: str,
    block_type: str,
    headings_path: list[str],
    char_start: int,
    char_end: int,
    block_idx: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[dict[str, Any]]:
    """Split oversized markdown blocks while preserving structural boundaries.

    Structured blocks (`table`, `list`, `quote`) are split line-by-line without overlap.
    Fenced `code` blocks are emitted as a single chunk to avoid fence corruption.
    Paragraph-like content keeps token-window splitting with offset-accurate spans.
    """
    if block_type in {"table", "list", "code", "quote"}:
        overlap = 0
    else:
        overlap = max(0, min(overlap_tokens, max_tokens - 1))
    chunks: list[dict[str, Any]] = []

    if block_type == "code":
        return [
            {
                "chunk_type": "code",
                "chunk_path": "/".join(headings_path),
                "chunk_text": text,
                "token_count": _token_count(text),
                "char_start": char_start,
                "char_end": char_end,
                "block_start_idx": block_idx,
                "block_end_idx": block_idx,
            }
        ] if text else []

    if block_type in {"table", "list", "quote"}:
        lines = text.splitlines(keepends=True)
        if not lines:
            return []
        line_offsets: list[int] = []
        running = 0
        for raw_line in lines:
            line_offsets.append(running)
            running += len(raw_line)

        protected_idxs: set[int] = set()
        if block_type == "table" and len(lines) >= 2 and _is_table_header_line(lines[0]) and _is_table_separator_line(lines[1]):
            protected_idxs = {0, 1}

        buf: list[str] = []
        buf_start = 0
        buf_tokens = 0
        for idx, line in enumerate(lines):
            line_tokens = _token_count(line)
            would_overflow = bool(buf) and (buf_tokens + line_tokens > max_tokens)
            should_keep_with_buffer = idx in protected_idxs and any(p in protected_idxs for p in range(buf_start, idx + 1))
            if would_overflow and not should_keep_with_buffer:
                piece = "".join(buf)
                rel_start = line_offsets[buf_start]
                rel_end = line_offsets[idx]
                chunks.append(
                    {
                        "chunk_type": block_type,
                        "chunk_path": "/".join(headings_path),
                        "chunk_text": piece,
                        "token_count": _token_count(piece),
                        "char_start": char_start + rel_start,
                        "char_end": char_start + rel_end,
                        "block_start_idx": block_idx,
                        "block_end_idx": block_idx,
                    }
                )
                buf = []
                buf_start = idx
                buf_tokens = 0

            buf.append(line)
            buf_tokens += line_tokens

        if buf:
            piece = "".join(buf)
            rel_start = line_offsets[buf_start]
            chunks.append(
                {
                    "chunk_type": block_type,
                    "chunk_path": "/".join(headings_path),
                    "chunk_text": piece,
                    "token_count": _token_count(piece),
                    "char_start": char_start + rel_start,
                    "char_end": char_start + len(text),
                    "block_start_idx": block_idx,
                    "block_end_idx": block_idx,
                }
            )
        return chunks

    matches = list(re.finditer(r"\S+", text))
    if not matches:
        return []
    step = max(1, max_tokens - overlap)
    for i in range(0, len(matches), step):
        piece_matches = matches[i : i + max_tokens]
        if not piece_matches:
            break
        rel_start = piece_matches[0].start()
        rel_end = piece_matches[-1].end()
        piece = text[rel_start:rel_end]
        chunks.append(
            {
                "chunk_type": "mixed" if block_type == "paragraph" else block_type,
                "chunk_path": "/".join(headings_path),
                "chunk_text": piece,
                "token_count": _token_count(piece),
                "char_start": char_start + rel_start,
                "char_end": char_start + rel_end,
                "block_start_idx": block_idx,
                "block_end_idx": block_idx,
            }
        )
        if i + max_tokens >= len(matches):
            break
    return chunks


def chunk_markdown(
    markdown: str,
    *,
    target_tokens: int = 650,
    max_tokens: int = 900,
    min_tokens: int = 120,
    overlap_tokens: int = 80,
) -> list[dict[str, Any]]:
    blocks = _parse_markdown_blocks(markdown)
    if not blocks:
        return []

    built: list[dict[str, Any]] = []
    current_blocks: list[tuple[int, dict[str, Any]]] = []
    current_tokens = 0

    def flush(force: bool = False) -> None:
        nonlocal current_blocks, current_tokens
        if not current_blocks:
            return
        if not force and current_tokens < max(min_tokens, 1):
            return

        block_types = [b[1]["type"] for b in current_blocks]
        if len(set(block_types)) == 1:
            chunk_type = block_types[0]
        else:
            chunk_type = "mixed"
        built.append(
            {
                "chunk_type": chunk_type,
                "chunk_path": "/".join(current_blocks[0][1]["headings_path"]),
                "chunk_text": markdown[current_blocks[0][1]["char_start"] : current_blocks[-1][1]["char_end"]],
                "token_count": current_tokens,
                "char_start": current_blocks[0][1]["char_start"],
                "char_end": current_blocks[-1][1]["char_end"],
                "block_start_idx": current_blocks[0][0],
                "block_end_idx": current_blocks[-1][0],
            }
        )
        current_blocks = []
        current_tokens = 0

    for idx, block in enumerate(blocks):
        b_tokens = int(block["token_estimate"])
        if b_tokens > max_tokens:
            flush(force=True)
            built.extend(
                _split_large_block(
                    text=block["text"],
                    block_type=block["type"],
                    headings_path=block["headings_path"],
                    char_start=int(block["char_start"]),
                    char_end=int(block["char_end"]),
                    block_idx=idx,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens,
                )
            )
            continue

        would_be = current_tokens + b_tokens
        if current_blocks and would_be > max_tokens and current_tokens >= min_tokens:
            flush(force=True)

        current_blocks.append((idx, block))
        current_tokens += b_tokens
        if current_tokens >= target_tokens:
            flush(force=True)

    flush(force=True)
    return built


def stable_chunk_id(tenant_id: uuid.UUID, document_id: uuid.UUID, source_version_id: uuid.UUID, ordinal: int, chunk_text: str) -> uuid.UUID:
    canonical = _canonical_chunk_text(chunk_text)
    payload = f"{tenant_id}|{document_id}|{source_version_id}|{ordinal}|{canonical}"
    return uuid.UUID(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32])


def _upsert_source(db: Session, tenant_id: uuid.UUID, item: SourceItem) -> uuid.UUID:
    source_id = uuid.uuid4()
    result = db.execute(
        _sql(
            """
            INSERT INTO sources (source_id, tenant_id, source_type, external_ref, status)
            VALUES (:source_id, :tenant_id, :source_type, :external_ref, 'INDEXED')
            ON CONFLICT (tenant_id, source_type, external_ref)
            DO UPDATE SET status = 'INDEXED'
            RETURNING source_id
            """
        ),
        {"source_id": source_id, "tenant_id": tenant_id, "source_type": item.source_type, "external_ref": item.external_ref},
    )
    if hasattr(result, "mappings"):
        row = result.mappings().first()
        if row and row.get("source_id"):
            return row["source_id"]

    check = db.execute(
        _sql(
            """
            SELECT source_id
            FROM sources
            WHERE tenant_id = :tenant_id
              AND source_type = :source_type
              AND external_ref = :external_ref
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "source_type": item.source_type, "external_ref": item.external_ref},
    )
    if hasattr(check, "mappings"):
        row = check.mappings().first()
        if row and row.get("source_id"):
            return row["source_id"]
    return source_id


def _find_source_version_id(db: Session, source_id: uuid.UUID, checksum: str) -> uuid.UUID | None:
    existing = db.execute(
        _sql(
            """
            SELECT source_version_id
            FROM source_versions
            WHERE source_id = :source_id
              AND checksum = :checksum
            LIMIT 1
            """
        ),
        {"source_id": source_id, "checksum": checksum},
    )
    if not hasattr(existing, "mappings"):
        return None
    row = existing.mappings().first()
    if not row:
        return None
    return row.get("source_version_id")


def _insert_source_version(
    db: Session,
    source_id: uuid.UUID,
    checksum: str,
    s3_raw_uri: str,
    s3_markdown_uri: str,
) -> tuple[uuid.UUID, bool]:
    existing_version_id = _find_source_version_id(db, source_id, checksum)
    if existing_version_id is not None:
        return existing_version_id, False

    source_version_id = uuid.uuid4()
    insert_result = db.execute(
        _sql(
            """
            INSERT INTO source_versions (
                source_version_id, source_id, version_label, checksum, s3_raw_uri, s3_markdown_uri, metadata_json
            ) VALUES (:source_version_id, :source_id, :version_label, :checksum, :s3_raw_uri, :s3_markdown_uri, :metadata_json)
            ON CONFLICT (source_id, checksum) DO NOTHING
            RETURNING source_version_id
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
    if hasattr(insert_result, "mappings"):
        row = insert_result.mappings().first()
        if row and row.get("source_version_id"):
            return row["source_version_id"], True

    existing_version_id = _find_source_version_id(db, source_id, checksum)
    if existing_version_id is not None:
        return existing_version_id, False
    return source_version_id, True


def _get_existing_document_id(db: Session, source_version_id: uuid.UUID) -> uuid.UUID | None:
    result = db.execute(
        _sql(
            """
            SELECT document_id
            FROM documents
            WHERE source_version_id = :source_version_id
            ORDER BY updated_date DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"source_version_id": source_version_id},
    )
    if not hasattr(result, "mappings"):
        return None
    row = result.mappings().first()
    if not row:
        return None
    return row.get("document_id")


def _list_existing_chunk_ids(db: Session, document_id: uuid.UUID) -> list[uuid.UUID]:
    result = db.execute(
        _sql(
            """
            SELECT chunk_id
            FROM chunks
            WHERE document_id = :document_id
            ORDER BY ordinal
            """
        ),
        {"document_id": document_id},
    )
    if not hasattr(result, "mappings"):
        return []
    return [row["chunk_id"] for row in result.mappings().all()]


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
    cfg = _load_settings()
    chunk_defs = chunk_markdown(
        markdown,
        target_tokens=int(getattr(cfg, "CHUNK_TARGET_TOKENS", 650)),
        max_tokens=int(getattr(cfg, "CHUNK_MAX_TOKENS", 900)),
        min_tokens=int(getattr(cfg, "CHUNK_MIN_TOKENS", 120)),
        overlap_tokens=int(getattr(cfg, "CHUNK_OVERLAP_TOKENS", 80)),
    )

    chunk_ids: list[uuid.UUID] = []
    for ordinal, chunk in enumerate(chunk_defs):
        chunk_path = str(chunk.get("chunk_path", ""))
        chunk_text = str(chunk.get("chunk_text", ""))
        chunk_id = stable_chunk_id(tenant_id, document_id, source_version_id, ordinal, chunk_text)
        chunk_ids.append(chunk_id)
        db.execute(
            _sql(
                """
                INSERT INTO chunks (
                    chunk_id, document_id, tenant_id, chunk_path, chunk_text, token_count, ordinal,
                    chunk_type, char_start, char_end, block_start_idx, block_end_idx
                )
                VALUES (
                    :chunk_id, :document_id, :tenant_id, :chunk_path, :chunk_text, :token_count, :ordinal,
                    :chunk_type, :char_start, :char_end, :block_start_idx, :block_end_idx
                )
                """
            ),
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "tenant_id": tenant_id,
                "chunk_path": chunk_path,
                "chunk_text": chunk_text,
                "token_count": int(chunk.get("token_count", _token_count(chunk_text))),
                "ordinal": ordinal,
                "chunk_type": str(chunk.get("chunk_type", "mixed")),
                "char_start": int(chunk.get("char_start", 0)),
                "char_end": int(chunk.get("char_end", 0)),
                "block_start_idx": int(chunk.get("block_start_idx", 0)),
                "block_end_idx": int(chunk.get("block_end_idx", 0)),
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


def _build_embedding_text(chunk_path: str, chunk_text: str) -> str:
    path = chunk_path.strip()
    if not path:
        return chunk_text
    return f"[H] {path}\n{chunk_text}"


def _upsert_chunk_vectors(db: Session, tenant_id: uuid.UUID, chunk_ids: list[uuid.UUID]) -> None:
    if not chunk_ids:
        return
    cfg = _load_settings()
    batch_size = int(getattr(cfg, "EMBEDDINGS_BATCH_SIZE", 64))
    retry_attempts = int(getattr(cfg, "EMBEDDINGS_RETRY_ATTEMPTS", 3))
    model_id = str(getattr(cfg, "EMBEDDINGS_DEFAULT_MODEL_ID", "bge-m3"))
    client = EmbeddingsClient(getattr(cfg, "EMBEDDINGS_SERVICE_URL", None), getattr(cfg, "EMBEDDINGS_TIMEOUT_SECONDS", 30))

    query_result = db.execute(
        _sql(
            """
            SELECT c.chunk_id, c.chunk_path, c.chunk_text
            FROM chunks c
            LEFT JOIN chunk_vectors cv ON cv.chunk_id = c.chunk_id
            WHERE c.tenant_id = :tenant_id
              AND c.chunk_id = ANY(:chunk_ids)
              AND cv.chunk_id IS NULL
            ORDER BY c.ordinal
            """
        ),
        {"tenant_id": tenant_id, "chunk_ids": chunk_ids},
    )
    if not hasattr(query_result, "mappings"):
        return
    rows = query_result.mappings().all()

    vectors_indexed_count = 0
    batch_count = 0
    start_all = time.perf_counter()

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        t0 = datetime.now(timezone.utc)
        texts = [_build_embedding_text(str(row.get("chunk_path") or ""), str(row["chunk_text"])) for row in batch]
        correlation_id = str(uuid.uuid4())
        _log_ingest_event(
            db,
            tenant_id,
            "EMBEDDINGS_REQUEST",
            {
                "model": model_id,
                "batch_size": len(batch),
                "chunk_ids": [str(row["chunk_id"]) for row in batch],
            },
        )

        last_exc: Exception | None = None
        embeddings: list[list[float]] | None = None
        for attempt in range(1, max(retry_attempts, 1) + 1):
            try:
                embeddings = client.embed_texts(
                    texts,
                    model_id=model_id,
                    tenant_id=str(tenant_id),
                    correlation_id=correlation_id,
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max(retry_attempts, 1):
                    delay_seconds = min(2 ** (attempt - 1), 8)
                    time.sleep(delay_seconds)

        if embeddings is None:
            _log_ingest_event(
                db,
                tenant_id,
                "ERROR",
                {
                    "code": "S-EMB-INDEX-FAILED",
                    "message": str(last_exc),
                    "batch_start": i,
                    "attempts": max(retry_attempts, 1),
                },
            )
            raise EmbeddingIndexingError("S-EMB-INDEX-FAILED") from last_exc

        if len(embeddings) != len(batch):
            raise EmbeddingIndexingError("S-EMB-INDEX-FAILED")

        for row, emb in zip(batch, embeddings):
            db.execute(
                _sql(
                    """
                    INSERT INTO chunk_vectors (chunk_id, tenant_id, embedding_model, embedding, embedding_dim, embedding_input_mode)
                    VALUES (:chunk_id, :tenant_id, :embedding_model, CAST(:embedding AS vector), :embedding_dim, :embedding_input_mode)
                    ON CONFLICT (chunk_id) DO UPDATE
                    SET tenant_id = EXCLUDED.tenant_id,
                        embedding_model = EXCLUDED.embedding_model,
                        embedding = EXCLUDED.embedding,
                        embedding_dim = EXCLUDED.embedding_dim,
                        embedding_input_mode = EXCLUDED.embedding_input_mode,
                        updated_at = now()
                    """
                ),
                {
                    "chunk_id": row["chunk_id"],
                    "tenant_id": tenant_id,
                    "embedding_model": model_id,
                    "embedding": "[" + ",".join(f"{float(x):.8f}" for x in emb) + "]",
                    "embedding_dim": len(emb),
                    "embedding_input_mode": "path_text_v2",
                },
            )
        elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
        _log_ingest_event(
            db,
            tenant_id,
            "EMBEDDINGS_RESPONSE",
            {
                "model": model_id,
                "batch_size": len(batch),
                "duration_ms": elapsed_ms,
                "indexed_count": len(batch),
            },
        )
        _log_ingest_event(db, tenant_id, "PIPELINE_STAGE", {"stage": "INDEX_VECTOR", "batch_size": len(batch), "duration_ms": elapsed_ms})
        vectors_indexed_count += len(batch)
        batch_count += 1

    duration_ms = int((time.perf_counter() - start_all) * 1000)
    LOGGER.info(
        "embeddings_indexing_completed",
        extra={
            "request_id": None,
            "tenant_id": str(tenant_id),
            "vectors_indexed_count": vectors_indexed_count,
            "batch_count": batch_count,
            "duration_ms": duration_ms,
        },
    )


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


def ingest_source_items(
    db: Session,
    tenant_id: uuid.UUID,
    items: list[SourceItem],
    storage: StorageAdapter | None = None,
    raw_payloads: dict[str, bytes] | None = None,
) -> dict[str, int]:
    storage = storage or _default_storage()
    raw_payloads = raw_payloads or {}

    docs = chunks = links = artifacts = 0
    for item in items:
        markdown = normalize_to_markdown(item.markdown)
        source_id = _upsert_source(db, tenant_id, item)

        cfg = _load_settings()
        raw_payload = raw_payloads.get(item.external_ref)
        raw_key = f"{tenant_id}/{source_id}/raw.bin" if raw_payload is not None else f"{tenant_id}/{source_id}/raw.txt"
        md_key = f"{tenant_id}/{source_id}/normalized.md"

        checksum = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        source_version_id = _find_source_version_id(db, source_id, checksum)
        if source_version_id is None:
            if raw_payload is not None and hasattr(storage, "put_bytes"):
                raw_uri = storage.put_bytes(cfg.S3_BUCKET_RAW, raw_key, raw_payload)
            else:
                raw_uri = storage.put_text(cfg.S3_BUCKET_RAW, raw_key, item.markdown)
            md_uri = storage.put_text(cfg.S3_BUCKET_MARKDOWN, md_key, markdown)
            source_version_id, created_source_version = _insert_source_version(db, source_id, checksum, raw_uri, md_uri)
        else:
            created_source_version = False
        document_id = _get_existing_document_id(db, source_version_id)

        if created_source_version or document_id is None:
            document_id = _insert_document(db, tenant_id, source_id, source_version_id, item)
            chunk_ids = _insert_chunks(db, tenant_id, document_id, source_version_id, markdown)
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
        else:
            chunk_ids = _list_existing_chunk_ids(db, document_id)

        _upsert_chunk_vectors(db, tenant_id, chunk_ids)
        _upsert_fts_for_chunks(db, tenant_id, chunk_ids)

    if hasattr(db, "commit"):
        db.commit()
    return {"documents": docs, "chunks": chunks, "cross_links": links, "artifacts": artifacts}




def should_fetch(descriptor: SourceDescriptor, state: Any, incremental_enabled: bool) -> bool:
    if not incremental_enabled:
        return True
    if state is None:
        return True
    if descriptor.last_modified and (state.last_seen_modified_at is None or descriptor.last_modified > state.last_seen_modified_at):
        return True
    if descriptor.checksum_hint and descriptor.checksum_hint != state.last_seen_checksum:
        return True
    return False


def ingest_sources_sync(
    db: Session,
    tenant_id: uuid.UUID,
    source_types: list[str],
    confluence: Any | None = None,
    file_catalog: Any | None = None,
    storage: StorageAdapter | None = None,
    connector_registry: Any | None = None,
) -> dict[str, int]:
    if (confluence is not None or file_catalog is not None) or not settings.CONNECTOR_REGISTRY_ENABLED:
        items: list[SourceItem] = []
        if confluence and ("CONFLUENCE_PAGE" in source_types or "CONFLUENCE_ATTACHMENT" in source_types):
            items.extend(confluence.crawl(tenant_id))
        if file_catalog and "FILE_CATALOG_OBJECT" in source_types:
            items.extend(file_catalog.crawl(tenant_id))
        return ingest_source_items(db, tenant_id, items, storage=storage)

    connector_registry = connector_registry or register_default_connectors()
    sync_context = SyncContext(
        max_items_per_run=settings.CONNECTOR_SYNC_MAX_ITEMS_PER_RUN,
        page_size=settings.CONNECTOR_SYNC_PAGE_SIZE,
        incremental_enabled=settings.CONNECTOR_INCREMENTAL_ENABLED,
    )
    repo = SourceSyncStateRepository(db)
    items: list[SourceItem] = []
    descriptor_by_ref: dict[str, SourceDescriptor] = {}
    raw_payloads: dict[str, bytes] = {}
    seen_refs_by_source_type: dict[str, set[str]] = {}
    counters = {
        "descriptors_listed": 0,
        "items_fetched": 0,
        "items_skipped_incremental": 0,
        "items_ingested": 0,
        "items_failed": 0,
    }

    for source_type in source_types:
        connector = connector_registry.get(source_type)
        descriptors = connector.list_descriptors(str(tenant_id), sync_context)[: settings.CONNECTOR_SYNC_MAX_ITEMS_PER_RUN]
        counters["descriptors_listed"] += len(descriptors)
        seen_refs_by_source_type[source_type] = {d.external_ref for d in descriptors}
        LOGGER.info("connector_list_descriptors", extra={"source_type": source_type, "descriptors": len(descriptors), "event": "connector_list_descriptors"})
        for descriptor in descriptors:
            state = repo.get_state(str(tenant_id), descriptor.source_type, descriptor.external_ref)
            if not should_fetch(descriptor, state, settings.CONNECTOR_INCREMENTAL_ENABLED):
                counters["items_skipped_incremental"] += 1
                LOGGER.info(
                    "file_catalog_skip_incremental",
                    extra={
                        "event": "file_catalog_skip_incremental",
                        "source_type": descriptor.source_type,
                        "external_ref": descriptor.external_ref,
                    },
                )
                continue
            result = connector.fetch_item(str(tenant_id), descriptor)
            if result.error or result.item is None:
                counters["items_failed"] += 1
                repo.mark_failure(
                    tenant_id=str(tenant_id),
                    source_type=descriptor.source_type,
                    external_ref=descriptor.external_ref,
                    last_seen_modified_at=descriptor.last_modified,
                    last_seen_checksum=descriptor.checksum_hint,
                    last_synced_at=datetime.now(timezone.utc),
                    error_code=(result.error.error_code if result.error else "I-CONNECTOR-EMPTY-ITEM"),
                    error_message=(result.error.message if result.error else "Connector returned empty item"),
                )
                continue
            counters["items_fetched"] += 1
            descriptor_by_ref[descriptor.external_ref] = descriptor
            items.append(result.item)
            if result.raw_payload is not None:
                raw_payloads[result.item.external_ref] = result.raw_payload

    for source_type, seen_refs in seen_refs_by_source_type.items():
        previous_refs = set(repo.list_external_refs(str(tenant_id), source_type))
        deleted_refs = previous_refs - seen_refs
        for external_ref in sorted(deleted_refs):
            repo.mark_deleted(
                tenant_id=str(tenant_id),
                source_type=source_type,
                external_ref=external_ref,
                last_synced_at=datetime.now(timezone.utc),
            )

    ingest_result = ingest_source_items(db, tenant_id, items, storage=storage, raw_payloads=raw_payloads)
    counters["items_ingested"] = ingest_result["documents"]

    for item in items:
        desc = descriptor_by_ref.get(item.external_ref)
        repo.mark_success(
            tenant_id=str(tenant_id),
            source_type=item.source_type,
            external_ref=item.external_ref,
            last_seen_modified_at=(desc.last_modified if desc else None),
            last_seen_checksum=(desc.checksum_hint if desc else None),
            last_synced_at=datetime.now(timezone.utc),
        )

    LOGGER.info("connector_summary", extra={"event": "connector_summary", "tenant_id": str(tenant_id), **counters})
    return ingest_result
