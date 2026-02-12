import uuid

import pytest

from app.services.ingestion import (
    EmbeddingIndexingError,
    SourceItem,
    _parse_markdown_blocks,
    _token_count,
    _upsert_chunk_vectors,
    chunk_markdown,
    ingest_sources_sync,
    stable_chunk_id,
)


class FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeResult:
    rowcount = 1

    def __init__(self, rows=None):
        self._rows = rows or []

    def mappings(self):
        return FakeMappings(self._rows)


class FakeDb:
    def __init__(self):
        self.calls = []
        self.sources = {}
        self.source_versions = {}
        self.documents_by_version = {}
        self.chunks_by_document = {}
        self.chunk_texts = {}

    def execute(self, statement, params=None):
        stmt = str(statement)
        payload = params or {}
        self.calls.append((stmt, payload))
        if "SELECT source_id" in stmt and "FROM sources" in stmt:
            key = (payload.get("tenant_id"), payload.get("source_type"), payload.get("external_ref"))
            source_id = self.sources.get(key)
            return FakeResult([] if source_id is None else [{"source_id": source_id}])
        if "INSERT INTO sources" in stmt:
            key = (payload.get("tenant_id"), payload.get("source_type"), payload.get("external_ref"))
            source_id = self.sources.setdefault(key, payload.get("source_id"))
            return FakeResult([{"source_id": source_id}]) if "RETURNING source_id" in stmt else FakeResult()

        if "SELECT source_version_id" in stmt and "FROM source_versions" in stmt:
            key = (payload.get("source_id"), payload.get("checksum"))
            version_id = self.source_versions.get(key)
            return FakeResult([] if version_id is None else [{"source_version_id": version_id}])
        if "INSERT INTO source_versions" in stmt:
            key = (payload.get("source_id"), payload.get("checksum"))
            existing = self.source_versions.get(key)
            if existing is not None:
                return FakeResult([])
            self.source_versions[key] = payload.get("source_version_id")
            return FakeResult([{"source_version_id": payload.get("source_version_id")}]) if "RETURNING source_version_id" in stmt else FakeResult()

        if "SELECT document_id" in stmt and "FROM documents" in stmt and "source_version_id" in stmt:
            version_id = payload.get("source_version_id")
            document_id = self.documents_by_version.get(version_id)
            return FakeResult([] if document_id is None else [{"document_id": document_id}])
        if "INSERT INTO documents" in stmt:
            self.documents_by_version[payload.get("source_version_id")] = payload.get("document_id")
            return FakeResult()

        if "SELECT chunk_id" in stmt and "FROM chunks" in stmt and "document_id" in stmt:
            ids = self.chunks_by_document.get(payload.get("document_id"), [])
            return FakeResult([{"chunk_id": chunk_id} for chunk_id in ids])
        if "INSERT INTO chunks" in stmt:
            document_id = payload.get("document_id")
            chunk_id = payload.get("chunk_id")
            self.chunks_by_document.setdefault(document_id, []).append(chunk_id)
            self.chunk_texts[chunk_id] = payload.get("chunk_text", "")
            return FakeResult()

        if "SELECT c.chunk_id, c.chunk_text" in stmt and "LEFT JOIN chunk_vectors" in stmt:
            chunk_ids = payload.get("chunk_ids", [])
            return FakeResult([{"chunk_id": cid, "chunk_text": self.chunk_texts.get(cid, "chunk text")} for cid in chunk_ids])
        return FakeResult()

    def commit(self):
        return None


class FakeStorage:
    def __init__(self):
        self.put_calls = []

    def put_text(self, bucket: str, key: str, text: str) -> str:
        self.put_calls.append((bucket, key, text))
        return f"s3://{bucket}/{key}"


class FakeConfluence:
    def crawl(self, tenant_id):
        return [
            SourceItem(
                source_type="CONFLUENCE_PAGE",
                external_ref="page:1",
                title="Policy",
                markdown="# Policy\nVacation policy text with [link](https://conf.local/page/2)",
                url="https://conf.local/page/1",
                author="admin",
                labels=["hr"],
            )
        ]


class FakeCatalog:
    def crawl(self, tenant_id):
        return [
            SourceItem(
                source_type="FILE_CATALOG_OBJECT",
                external_ref="file:a.md",
                title="Catalog",
                markdown="# Catalog\nAttachment content",
            )
        ]


def test_stable_chunk_id_is_deterministic_positive():
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    doc = uuid.UUID("22222222-2222-2222-2222-222222222222")
    ver = uuid.UUID("33333333-3333-3333-3333-333333333333")
    c1 = stable_chunk_id(tenant, doc, ver, 0, "same text")
    c2 = stable_chunk_id(tenant, doc, ver, 0, "same   text")
    assert c1 == c2


def test_chunk_markdown_negative_empty():
    assert chunk_markdown("   \n\n") == []


def test_ingest_sources_sync_inserts_docs_chunks_links_and_s3_positive(monkeypatch):
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    result = ingest_sources_sync(
        db,
        tenant,
        ["CONFLUENCE_PAGE", "FILE_CATALOG_OBJECT"],
        confluence=FakeConfluence(),
        file_catalog=FakeCatalog(),
        storage=storage,
    )
    assert result["documents"] == 2
    assert result["chunks"] >= 2
    assert result["cross_links"] >= 1
    assert result["artifacts"] == 2

    sql_text = "\n".join(call[0] for call in db.calls)
    assert "INSERT INTO documents" in sql_text
    assert "INSERT INTO chunks" in sql_text
    assert "INSERT INTO cross_links" in sql_text
    assert "INSERT INTO source_versions" in sql_text
    assert "INSERT INTO chunk_vectors" in sql_text
    assert "INSERT INTO chunk_fts" in sql_text

    buckets = [x[0] for x in storage.put_calls]
    assert "rag-raw" in buckets
    assert "rag-markdown" in buckets


def test_ingest_sources_sync_negative_unknown_source_type_no_data():
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    result = ingest_sources_sync(db, tenant, ["UNKNOWN"], storage=storage)
    assert result == {"documents": 0, "chunks": 0, "cross_links": 0, "artifacts": 0}
    assert db.calls == []
    assert storage.put_calls == []


def test_ingest_sources_sync_repeated_run_is_idempotent_for_sources_versions_documents_and_chunks(monkeypatch):
    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    first = ingest_sources_sync(db, tenant, ["CONFLUENCE_PAGE"], confluence=FakeConfluence(), storage=storage)
    first_storage_calls = len(storage.put_calls)
    second = ingest_sources_sync(db, tenant, ["CONFLUENCE_PAGE"], confluence=FakeConfluence(), storage=storage)

    assert first["documents"] == 1
    assert first["chunks"] >= 1
    assert second["documents"] == 0
    assert second["chunks"] == 0
    assert len(storage.put_calls) == first_storage_calls

    source_insert_calls = [sql for sql, _ in db.calls if "INSERT INTO sources" in sql]
    source_version_calls = [sql for sql, _ in db.calls if "INSERT INTO source_versions" in sql]
    document_calls = [sql for sql, _ in db.calls if "INSERT INTO documents" in sql]
    chunk_calls = [sql for sql, _ in db.calls if "INSERT INTO chunks" in sql]
    assert len(source_insert_calls) == 2
    assert len(source_version_calls) == 1
    assert len(document_calls) == 1
    assert len(chunk_calls) == first["chunks"]


def test_insert_source_version_returns_existing_for_same_checksum():
    from app.services.ingestion import _insert_source_version

    db = FakeDb()
    source_id = uuid.uuid4()
    checksum = "abc123"

    first_id, first_created = _insert_source_version(db, source_id, checksum, "s3://raw/1", "s3://md/1")
    second_id, second_created = _insert_source_version(db, source_id, checksum, "s3://raw/2", "s3://md/2")

    assert first_created is True
    assert second_created is False
    assert first_id == second_id


def test_upsert_source_returns_same_id_on_duplicate_positive():
    from app.services.ingestion import _upsert_source

    db = FakeDb()
    tenant_id = uuid.uuid4()
    item = SourceItem(source_type="CONFLUENCE_PAGE", external_ref="page:1", title="T", markdown="# T")

    first = _upsert_source(db, tenant_id, item)
    second = _upsert_source(db, tenant_id, item)

    assert first == second


def test_upsert_chunk_vectors_retries_then_succeeds(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    calls = {"n": 0}

    class RetryEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("temporary")
            return [[0.1, 0.2, 0.3] for _ in texts]

    class FakeSettings:
        EMBEDDINGS_BATCH_SIZE = 2
        EMBEDDINGS_RETRY_ATTEMPTS = 3
        EMBEDDINGS_DEFAULT_MODEL_ID = "bge-m3"
        EMBEDDINGS_SERVICE_URL = "http://localhost:8200"
        EMBEDDINGS_TIMEOUT_SECONDS = 30

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", RetryEmbeddingsClient)
    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.ingestion.time.sleep", lambda *_args, **_kwargs: None)

    chunk_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    _upsert_chunk_vectors(db, tenant, chunk_ids)

    assert calls["n"] == 3
    sql_text = "\n".join(call[0] for call in db.calls)
    assert "LEFT JOIN chunk_vectors" in sql_text
    assert "ON CONFLICT (chunk_id) DO UPDATE" in sql_text


def test_upsert_chunk_vectors_raises_after_retries_exhausted(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")

    class AlwaysFailEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            raise RuntimeError("down")

    class FakeSettings:
        EMBEDDINGS_BATCH_SIZE = 2
        EMBEDDINGS_RETRY_ATTEMPTS = 2
        EMBEDDINGS_DEFAULT_MODEL_ID = "bge-m3"
        EMBEDDINGS_SERVICE_URL = "http://localhost:8200"
        EMBEDDINGS_TIMEOUT_SECONDS = 30

    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", AlwaysFailEmbeddingsClient)
    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.services.ingestion.time.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(EmbeddingIndexingError):
        _upsert_chunk_vectors(db, tenant, [uuid.uuid4()])


def test_chunk_markdown_respects_min_max_and_overlap_positive():
    text = "# H1\n" + ("alpha " * 1000)
    chunks = chunk_markdown(text, target_tokens=650, max_tokens=900, min_tokens=120, overlap_tokens=80)

    assert len(chunks) >= 2
    assert all(c["token_count"] <= 900 for c in chunks)
    # overlap for paragraph/mixed keeps repeated boundary tokens
    first_tail = chunks[0]["chunk_text"].split()[-5:]
    second_head = chunks[1]["chunk_text"].split()[:5]
    assert first_tail == second_head


def test_chunk_markdown_contract_boundaries_positive():
    markdown = """# Policy

Paragraph one sentence.

- item one
- item two

> quoted text

```
code line
```
"""
    chunks = chunk_markdown(markdown, target_tokens=20, max_tokens=40, min_tokens=1, overlap_tokens=5)

    assert chunks
    assert all("chunk_type" in c for c in chunks)
    assert all(c["char_end"] >= c["char_start"] for c in chunks)
    assert all(c["block_end_idx"] >= c["block_start_idx"] for c in chunks)


def test_parse_markdown_blocks_heading_level_h1_positive():
    blocks = _parse_markdown_blocks("# H1\n\nparagraph\n")
    assert blocks[0]["headings_path"] == ["H1"]


def test_parse_markdown_blocks_heading_level_with_leading_spaces_positive():
    markdown = "# H1\n\n  ## H2\n\nbody\n"
    blocks = _parse_markdown_blocks(markdown)
    assert blocks[0]["headings_path"] == ["H1", "H2"]


def test_parse_markdown_blocks_single_pipe_line_is_not_table_negative():
    blocks = _parse_markdown_blocks("a | b | c\n")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"


def test_parse_markdown_blocks_detects_markdown_table_positive():
    markdown = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    blocks = _parse_markdown_blocks(markdown)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "table"




def test_parse_markdown_blocks_pipe_lines_without_separator_not_table_negative():
    markdown = """a | b | c
1 | 2 | 3
"""
    blocks = _parse_markdown_blocks(markdown)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"


def test_parse_markdown_blocks_separator_not_after_header_not_table_negative():
    markdown = """a | b | c
plain line
| --- | --- |
"""
    blocks = _parse_markdown_blocks(markdown)
    assert all(block["type"] != "table" for block in blocks)


def test_parse_markdown_blocks_heading_path_nested_positive():
    markdown = """# H1

## H2

### H3

body
"""
    blocks = _parse_markdown_blocks(markdown)
    assert blocks[0]["headings_path"] == ["H1", "H2", "H3"]

def test_chunk_markdown_split_large_code_block_preserves_fence_positive():
    markdown = "# H1\n\n```python\n" + "\n".join(f"print({i})" for i in range(120)) + "\n```\n"
    chunks = chunk_markdown(markdown, target_tokens=20, max_tokens=25, min_tokens=1, overlap_tokens=5)
    code_chunks = [c for c in chunks if c["chunk_type"] == "code"]
    assert len(code_chunks) == 1
    assert code_chunks[0]["chunk_text"].startswith("```python")
    assert code_chunks[0]["chunk_text"].rstrip().endswith("```")


def test_chunk_markdown_split_table_only_by_lines_positive():
    table = "| a | b |\n| --- | --- |\n" + "".join(f"| {i} | {i+1} |\n" for i in range(60))
    chunks = chunk_markdown(table, target_tokens=20, max_tokens=30, min_tokens=1, overlap_tokens=5)
    table_chunks = [c for c in chunks if c["chunk_type"] == "table"]
    assert len(table_chunks) >= 2
    for c in table_chunks:
        assert c["chunk_text"].endswith("\n")
        assert "\n|" in c["chunk_text"] or c["chunk_text"].startswith("|")




def test_chunk_markdown_split_table_keeps_header_with_separator_positive():
    table = """| h1 | h2 |
| --- | --- |
""" + "".join(f"| {i} | {i+1} |\n" for i in range(40))
    chunks = chunk_markdown(table, target_tokens=5, max_tokens=5, min_tokens=1, overlap_tokens=0)
    table_chunks = [c for c in chunks if c["chunk_type"] == "table"]
    assert table_chunks
    assert "| h1 | h2 |" in table_chunks[0]["chunk_text"]
    assert "| --- | --- |" in table_chunks[0]["chunk_text"]


def test_chunk_markdown_split_list_not_mid_item_positive():
    markdown = "\n".join(f"- item {i} with extra words" for i in range(80)) + "\n"
    chunks = chunk_markdown(markdown, target_tokens=20, max_tokens=25, min_tokens=1, overlap_tokens=5)
    list_chunks = [c for c in chunks if c["chunk_type"] == "list"]
    assert len(list_chunks) >= 2
    assert all(line.startswith("- ") for c in list_chunks for line in c["chunk_text"].splitlines() if line)


def test_chunk_markdown_char_offsets_extract_real_substring_positive():
    markdown = "# H1\n\nFirst paragraph line.\nSecond line.\n\n- item one\n- item two\n"
    chunks = chunk_markdown(markdown, target_tokens=10, max_tokens=12, min_tokens=1, overlap_tokens=2)
    for chunk in chunks:
        extracted = markdown[chunk["char_start"] : chunk["char_end"]]
        assert chunk["chunk_text"] == extracted


def test_token_estimator_split_mode_backward_compatible_positive(monkeypatch):
    monkeypatch.setenv("TOKEN_ESTIMATOR", "split")
    assert _token_count("alpha beta   gamma") == 3


def test_token_estimator_tiktoken_fallback_without_dependency_negative(monkeypatch):
    monkeypatch.setenv("TOKEN_ESTIMATOR", "tiktoken")
    assert _token_count("alpha beta") >= 2

def test_token_estimator_tiktoken_can_differ_when_installed_positive(monkeypatch):
    pytest.importorskip("tiktoken")
    monkeypatch.setenv("TOKEN_ESTIMATOR", "split")
    split_count = _token_count("hello,world")
    monkeypatch.setenv("TOKEN_ESTIMATOR", "tiktoken")
    tk_count = _token_count("hello,world")
    assert tk_count >= 1
    assert split_count == 1



def test_normalize_to_markdown_preserves_fenced_code_block_spacing():
    from app.services.ingestion import normalize_to_markdown

    markdown = """before    text
```
def test():
\tprint(  'x'  )
```
after    text
"""
    normalized = normalize_to_markdown(markdown)
    assert "before text" in normalized
    assert "after text" in normalized
    assert "\tprint(  'x'  )" in normalized


def test_normalize_to_markdown_preserves_nested_list_indentation():
    from app.services.ingestion import normalize_to_markdown

    markdown = "- parent\n    - nested    item\n"
    normalized = normalize_to_markdown(markdown)
    assert "\n    - nested item\n" in normalized


def test_normalize_to_markdown_does_not_deform_markdown_table():
    from app.services.ingestion import normalize_to_markdown

    markdown = "| Name | Value  A |\n| --- | --- |\n| Key | Multi   value |\n"
    normalized = normalize_to_markdown(markdown)
    assert normalized == markdown


def test_insert_chunks_writes_metadata_columns_positive(monkeypatch):
    db = FakeDb()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    document_id = uuid.uuid4()
    source_version_id = uuid.uuid4()

    class FakeSettings:
        CHUNK_TARGET_TOKENS = 650
        CHUNK_MAX_TOKENS = 900
        CHUNK_MIN_TOKENS = 120
        CHUNK_OVERLAP_TOKENS = 80

    monkeypatch.setattr("app.services.ingestion._load_settings", lambda: FakeSettings())

    from app.services.ingestion import _insert_chunks

    chunk_ids = _insert_chunks(db, tenant, document_id, source_version_id, "# T\n\ntext body")
    assert chunk_ids
    insert_calls = [x for x in db.calls if "INSERT INTO chunks" in x[0]]
    assert insert_calls
    params = insert_calls[0][1]
    assert "chunk_type" in params
    assert "char_start" in params
    assert "char_end" in params
    assert "block_start_idx" in params
    assert "block_end_idx" in params


def test_stub_file_byte_ingestor_is_declared_but_not_runtime_enabled():
    from app.services.ingestion import StubFileByteIngestor

    ingestor = StubFileByteIngestor()
    with pytest.raises(NotImplementedError):
        ingestor.ingest_bytes(uuid.uuid4(), "file:1", b"binary")
