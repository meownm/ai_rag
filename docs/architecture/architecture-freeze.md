# Architecture Freeze: Corporate RAG Platform

Status: **FROZEN** (architecture level)
Scope: multi-tenant corporate RAG with external embeddings service

---

## SP-A1: High-level architecture text (C4 + service boundaries)

### C4-Context
- **Primary actors**:
  - Employee User (internal knowledge consumer)
  - Tenant Admin (configures tenant settings, prompts, citations mode)
  - Platform Operator (observability, incident response)
- **External systems**:
  - Confluence On-Prem API
  - File Catalog Storage (S3/MinIO)
  - Enterprise LLM endpoint
  - Identity/group source represented in Postgres local groups mapping

### C4-Container
- **corporate-rag-service (FastAPI)**
  - Responsibilities:
    - query orchestration (intent, retrieval orchestration, response assembly)
    - hybrid retrieval pipeline orchestration (BM25 + pgvector)
    - reranking orchestration (cross-encoder)
    - tenant policy enforcement (`only_sources`, citations toggle, prompt templates)
    - job orchestration for ingest/index lifecycle
  - Forbidden responsibility: embeddings generation.
- **embeddings-service (FastAPI, separate process/container)**
  - Responsibilities:
    - text embedding generation over HTTP API
    - batch embedding and health/version endpoints
  - No retrieval logic and no tenant policy logic.
- **Postgres + pgvector**
  - relational metadata, tenant model, job state, logs, BM25 lexical index tables, vector storage.
- **S3/MinIO**
  - raw and normalized source artifacts (original binaries and markdown transforms).
- **Worker subsystem (logical container)**
  - ingestion/preprocessing/indexing jobs invoked by corporate-rag-service, state persisted in DB.

### C4-Component (corporate-rag-service)
- API Layer: authn/authz, tenant resolution via local group mapping.
- Ingest Orchestrator: source discovery, conversion to markdown, logical chunking, metadata extraction.
- Index Orchestrator:
  - BM25 document/chunk lex indexing
  - embedding-request client over HTTP to embeddings-service
  - vector upsert to pgvector tables
- Retrieval Engine:
  - lexical candidate fetch
  - vector candidate fetch
  - score normalization + fusion + metadata/link boosts
  - cross-encoder rerank
- Answer Composer:
  - strict `only_sources` guard
  - optional citations (tenant-level switch)
  - tenant prompt template application
- Audit/Observability writer:
  - structured event records into DB.

### Service boundary rules
1. corporate-rag-service and embeddings-service are always deployed and versioned independently.
2. All embedding operations are remote HTTP calls from RAG to embeddings-service.
3. Retrieval always executes hybrid strategy and reranker stage.
4. Source of truth for documents/blobs is S3/MinIO.

### Invariants check after SP-A1
- Separate services retained: **PASS**.
- Hybrid retrieval retained: **PASS**.
- Cross-encoder reranker retained: **PASS**.
- Embeddings inside RAG forbidden: **PASS**.
- Multi-tenant model retained: **PASS**.
- Document-level ACL inside tenant not introduced: **PASS**.
- S3/MinIO storage retained: **PASS**.
- No LLM in preprocessing: **PASS**.
- `only sources` retained: **PASS**.
- Enum/job status not mutated yet: **PASS**.
- Simplifications: **FORBIDDEN AND NOT APPLIED**.

---

## SP-A2: Data model (logical + tables)

### Logical model
- Tenant owns settings, prompts, sources, jobs, logs, and queries.
- User access derived by `user_group_membership -> tenant_group_binding`.
- Source documents have versions, normalized markdown representations, chunk records, and index records.
- Search run stores candidate/score decomposition and final cited passages.

### Core tables
1. `tenants`
   - `tenant_id (pk, uuid)`
   - `tenant_key (unique)`
   - `display_name`
   - `is_active`
   - `created_at`, `updated_at`
2. `tenant_settings`
   - `tenant_id (pk/fk tenants)`
   - `citations_mode` (enum)
   - `only_sources_mode` (enum)
   - `default_prompt_template`
   - `metadata_boost_profile` (jsonb)
   - `link_boost_profile` (jsonb)
3. `local_groups`
   - `group_id (pk)`
   - `group_name (unique)`
4. `tenant_group_bindings`
   - `tenant_id (fk)`
   - `group_id (fk)`
   - `role` (enum tenant role)
5. `users`
   - `user_id (pk)`
   - `principal_name`
   - `display_name`
6. `user_group_memberships`
   - `user_id (fk)`
   - `group_id (fk)`
7. `sources`
   - `source_id (pk)`
   - `tenant_id (fk)`
   - `source_type` (enum)
   - `external_ref` (e.g., confluence page_id/catalog path)
   - `status` (enum source status)
   - `created_at`, `updated_at`
8. `source_versions`
   - `source_version_id (pk)`
   - `source_id (fk)`
   - `version_label`
   - `checksum`
   - `s3_raw_uri`
   - `s3_markdown_uri`
   - `metadata_json` (jsonb)
   - `discovered_at`
9. `documents`
   - `document_id (pk)`
   - `tenant_id (fk)`
   - `source_id (fk)`
   - `source_version_id (fk)`
   - `title`, `author`
   - `created_date`, `updated_date`
   - `space_key`, `page_id`, `parent_id`, `url`, `labels` (jsonb)
10. `document_links`
    - `from_document_id (fk)`
    - `to_document_id (fk nullable when unresolved)`
    - `link_url`
    - `link_type` (enum)
11. `chunks`
    - `chunk_id (pk)`
    - `document_id (fk)`
    - `tenant_id (fk)`
    - `chunk_path` (heading/list/table path)
    - `chunk_text`
    - `token_count`
    - `ordinal`
12. `chunk_fts`
    - `chunk_id (pk/fk)`
    - `tenant_id`
    - `fts_doc` (tsvector)
13. `chunk_vectors`
    - `chunk_id (pk/fk)`
    - `tenant_id`
    - `embedding_model`
    - `embedding vector` (pgvector)
    - `embedding_dim`
14. `ingest_jobs`
    - `job_id (pk)`
    - `tenant_id`
    - `job_type` (enum)
    - `job_status` (enum)
    - `requested_by`
    - `started_at`, `finished_at`
    - `error_code`, `error_message`
15. `search_requests`
    - `search_id (pk)`
    - `tenant_id`
    - `user_id`
    - `query_text`
    - `citations_requested`
16. `search_candidates`
    - `search_id (fk)`
    - `chunk_id (fk)`
    - `lex_score`, `vec_score`, `rerank_score`
    - `boosts_json`
    - `final_score`
    - `rank_position`
17. `answers`
    - `answer_id (pk)`
    - `search_id (fk)`
    - `answer_text`
    - `only_sources_verdict` (enum)
    - `citations_json` (jsonb)
18. `pipeline_trace`
    - `trace_id (pk)`
    - `tenant_id`
    - `correlation_id`
    - `stage` (enum)
    - `status` (enum)
    - `started_at`, `ended_at`
    - `payload_json` (jsonb)
19. `event_logs`
    - `event_id (pk)`
    - `tenant_id`
    - `correlation_id`
    - `event_type` (enum)
    - `log_data_mode` (enum)
    - `payload_json` (jsonb)
    - `duration_ms`
    - `created_at`

### Invariants check after SP-A2
All architectural invariants preserved; no simplifications introduced.

---

## SP-A3: OpenAPI contracts
Contracts frozen in files:
- `openapi/rag.yaml`
- `openapi/embeddings.yaml`

### Invariants check after SP-A3
Contracts preserve separate services, HTTP boundary for embeddings, hybrid retrieval + rerank semantics, and only-sources/citations constraints.
Simplifications forbidden and not applied.

---

## SP-A4: Enum registry (complete)

Enum freeze marker: `ENUM_FREEZE_V1`.

- `source_type`: `CONFLUENCE_PAGE`, `CONFLUENCE_ATTACHMENT`, `FILE_CATALOG_OBJECT`
- `source_status`: `DISCOVERED`, `FETCHED`, `NORMALIZED`, `INDEXED`, `FAILED`
- `tenant_role`: `TENANT_ADMIN`, `TENANT_EDITOR`, `TENANT_VIEWER`
- `citations_mode`: `DISABLED`, `OPTIONAL`, `REQUIRED`
- `only_sources_mode`: `STRICT`
- `job_type`: `SYNC_CONFLUENCE`, `SYNC_FILE_CATALOG`, `PREPROCESS`, `INDEX_LEXICAL`, `INDEX_VECTOR`, `REINDEX_ALL`
- `job_status`: `queued`, `processing`, `retrying`, `done`, `error`, `canceled`, `expired`
- `link_type`: `CONFLUENCE_PAGE_LINK`, `EXTERNAL_URL`, `ATTACHMENT_LINK`
- `pipeline_stage`: `INGEST_DISCOVERY`, `INGEST_FETCH`, `NORMALIZE_MARKDOWN`, `STRUCTURE_PARSE`, `CHUNK_LOGICAL`, `INDEX_BM25`, `EMBED_REQUEST`, `INDEX_VECTOR`, `SEARCH_LEXICAL`, `SEARCH_VECTOR`, `FUSION_BOOST`, `RERANK`, `ANSWER_COMPOSE`, `ANSWER_VALIDATE_ONLY_SOURCES`
- `pipeline_stage_status`: `STARTED`, `COMPLETED`, `FAILED`, `SKIPPED`
- `event_type`: `API_REQUEST`, `API_RESPONSE`, `EMBEDDINGS_REQUEST`, `EMBEDDINGS_RESPONSE`, `LLM_REQUEST`, `LLM_RESPONSE`, `PIPELINE_STAGE`, `ERROR`
- `log_data_mode`: `PLAIN`, `MASKED`, `HASHED`
- `error_code`:
  - `AUTH_UNAUTHORIZED`
  - `AUTH_FORBIDDEN_TENANT`
  - `TENANT_NOT_FOUND`
  - `SOURCE_NOT_FOUND`
  - `SOURCE_FETCH_FAILED`
  - `NORMALIZATION_FAILED`
  - `CHUNKING_FAILED`
  - `EMBEDDINGS_HTTP_ERROR`
  - `EMBEDDINGS_TIMEOUT`
  - `VECTOR_INDEX_ERROR`
  - `LEXICAL_INDEX_ERROR`
  - `RERANKER_ERROR`
  - `ONLY_SOURCES_VIOLATION`
  - `LLM_PROVIDER_ERROR`
  - `VALIDATION_ERROR`
  - `RATE_LIMITED`
  - `INTERNAL_ERROR`
- `only_sources_verdict`: `PASS`, `FAIL`

### Invariants check after SP-A4
Enum and job status now frozen (`ENUM_FREEZE_V1`); no later mutation allowed.
No simplifications introduced.

---

## SP-A5: Error model + job_status model

### Standard error envelope
- `error.code` (from `error_code` enum)
- `error.message` (human-readable)
- `error.details` (object)
- `error.correlation_id` (uuid)
- `error.retryable` (bool)
- `error.timestamp` (ISO8601)

### HTTP mapping
- 400: `VALIDATION_ERROR`
- 401: `AUTH_UNAUTHORIZED`
- 403: `AUTH_FORBIDDEN_TENANT`
- 404: `TENANT_NOT_FOUND`, `SOURCE_NOT_FOUND`
- 409: `ONLY_SOURCES_VIOLATION`
- 429: `RATE_LIMITED`
- 500: `INTERNAL_ERROR`, `LLM_PROVIDER_ERROR`, `RERANKER_ERROR`, `LEXICAL_INDEX_ERROR`, `VECTOR_INDEX_ERROR`
- 502: `EMBEDDINGS_HTTP_ERROR`
- 504: `EMBEDDINGS_TIMEOUT`

### Job status model
- Lifecycle graph:
  - `queued -> processing -> done`
  - `queued -> processing -> retrying -> processing -> done`
  - `queued -> processing -> retrying -> processing -> error`
  - `queued -> canceled`
  - `queued -> expired`
  - `processing -> canceled`
  - `processing -> expired`
- Terminal states: `done`, `error`, `canceled`, `expired`.
- Each terminal transition must write `finished_at`; failure states require `error_code`.

### Invariants check after SP-A5
Invariants preserved; job_status remains frozen and not altered further.
Simplifications forbidden and not applied.

---

## SP-A6: Observability model (logs schema + metrics)

### Structured DB log schema (`event_logs`)
- Required fields:
  - `event_id`, `tenant_id`, `correlation_id`, `event_type`, `log_data_mode`, `payload_json`, `duration_ms`, `created_at`
- `LOG_DATA_MODE` default: `PLAIN`.
- Payload conventions:
  - API events: route, method, status_code, request/response size
  - embeddings events: model, batch_size, latency_ms, http_status
  - llm events: provider/model, prompt_token_estimate, latency_ms
  - error events: `error_code`, stack fingerprint

### Metrics (Prometheus-style names)
- `rag_api_requests_total{route,tenant,status}`
- `rag_api_latency_ms_bucket{route,tenant}`
- `rag_retrieval_candidates_total{tenant,stage}`
- `rag_rerank_latency_ms_bucket{tenant}`
- `rag_only_sources_violations_total{tenant}`
- `rag_ingest_jobs_total{tenant,job_type,status}`
- `embeddings_http_calls_total{tenant,status}`
- `embeddings_http_latency_ms_bucket{tenant}`
- `llm_calls_total{tenant,status}`
- `llm_latency_ms_bucket{tenant}`

### Correlation rules
- One inbound API request generates a single `correlation_id` propagated through RAG, embeddings calls, LLM calls, and pipeline traces.

### Invariants check after SP-A6
Invariants preserved, including separate embeddings service logging and strict only-sources observability.
No simplifications introduced.

---

## SP-A7: Pipeline trace (ingest → index → search → answer)

1. **INGEST_DISCOVERY**
   - Discover Confluence pages/attachments and file-catalog objects for tenant.
2. **INGEST_FETCH**
   - Fetch raw object + metadata; persist raw blob in S3/MinIO.
3. **NORMALIZE_MARKDOWN**
   - Convert source format to markdown.
4. **STRUCTURE_PARSE**
   - Parse headings/tables/lists/paragraphs and extract metadata/link graph.
5. **CHUNK_LOGICAL**
   - Build logical chunks by content boundaries.
6. **INDEX_BM25**
   - Upsert lexical chunk records and `tsvector` data.
7. **EMBED_REQUEST**
   - Call embeddings-service `/v1/embeddings` via HTTP batch.
8. **INDEX_VECTOR**
   - Persist vectors into pgvector table.
9. **SEARCH_LEXICAL**
   - Query BM25/fts for candidate set.
10. **SEARCH_VECTOR**
    - Query vector similarity for candidate set.
11. **FUSION_BOOST**
    - Compute score breakdown: lex_score, vec_score, boosts.
12. **RERANK**
    - Run cross-encoder reranker and update rerank_score/final ranking.
13. **ANSWER_COMPOSE**
    - Compose response constrained by retrieved evidence and tenant prompt.
14. **ANSWER_VALIDATE_ONLY_SOURCES**
    - Enforce strict only-sources rule and produce citations if enabled.

Trace persistence:
- Each stage writes a `pipeline_trace` row with stage status and timing.

### Invariants check after SP-A7
Hybrid retrieval, reranker, and only-sources validation explicitly retained.
No simplifications introduced.

---

## SP-A8: Decision log (why choices made)

1. **Separate embeddings service** chosen for model agility/scaling isolation and invariant compliance.
2. **Hybrid retrieval** retained to balance lexical precision (acronyms/policies) and semantic recall.
3. **Cross-encoder reranker** retained for final precision in enterprise policy QA.
4. **Logical chunking** chosen to preserve document structure and citation fidelity.
5. **No LLM in preprocessing** to reduce hallucination risk and deterministic indexing.
6. **S3/MinIO mandatory** for artifact durability and reproducibility.
7. **Tenant by local Postgres groups** for on-prem compatibility and auditability.
8. **Only-sources strict mode** mandated to prevent unsupported assertions.
9. **Enum/job status freeze** to keep downstream integrations contract-stable.
10. **DB structured logs + correlation** chosen for audit/compliance traceability.

### Invariants check after SP-A8
All stated invariants verified as preserved.
Simplifications explicitly forbidden and not applied.

---

# ARCHITECTURE_FINGERPRINT
LIST_ENDPOINTS:
- corporate-rag-service: GET /v1/health
- corporate-rag-service: POST /v1/query
- corporate-rag-service: POST /v1/ingest/sources/sync
- corporate-rag-service: GET /v1/jobs/{job_id}
- embeddings-service: GET /v1/health
- embeddings-service: POST /v1/embeddings

LIST_ENUMS:
- source_type:
    - CONFLUENCE_PAGE
    - CONFLUENCE_ATTACHMENT
    - FILE_CATALOG_OBJECT
- source_status:
    - DISCOVERED
    - FETCHED
    - NORMALIZED
    - INDEXED
    - FAILED
- tenant_role:
    - TENANT_ADMIN
    - TENANT_EDITOR
    - TENANT_VIEWER
- citations_mode:
    - DISABLED
    - OPTIONAL
    - REQUIRED
- only_sources_mode:
    - STRICT
- job_type:
    - SYNC_CONFLUENCE
    - SYNC_FILE_CATALOG
    - PREPROCESS
    - INDEX_LEXICAL
    - INDEX_VECTOR
    - REINDEX_ALL
- job_status:
    - queued
    - processing
    - retrying
    - done
    - error
    - canceled
    - expired
- link_type:
    - CONFLUENCE_PAGE_LINK
    - EXTERNAL_URL
    - ATTACHMENT_LINK
- pipeline_stage:
    - INGEST_DISCOVERY
    - INGEST_FETCH
    - NORMALIZE_MARKDOWN
    - STRUCTURE_PARSE
    - CHUNK_LOGICAL
    - INDEX_BM25
    - EMBED_REQUEST
    - INDEX_VECTOR
    - SEARCH_LEXICAL
    - SEARCH_VECTOR
    - FUSION_BOOST
    - RERANK
    - ANSWER_COMPOSE
    - ANSWER_VALIDATE_ONLY_SOURCES
- pipeline_stage_status:
    - STARTED
    - COMPLETED
    - FAILED
    - SKIPPED
- event_type:
    - API_REQUEST
    - API_RESPONSE
    - EMBEDDINGS_REQUEST
    - EMBEDDINGS_RESPONSE
    - LLM_REQUEST
    - LLM_RESPONSE
    - PIPELINE_STAGE
    - ERROR
- log_data_mode:
    - PLAIN
    - MASKED
    - HASHED
- error_code:
    - AUTH_UNAUTHORIZED
    - AUTH_FORBIDDEN_TENANT
    - TENANT_NOT_FOUND
    - SOURCE_NOT_FOUND
    - SOURCE_FETCH_FAILED
    - NORMALIZATION_FAILED
    - CHUNKING_FAILED
    - EMBEDDINGS_HTTP_ERROR
    - EMBEDDINGS_TIMEOUT
    - VECTOR_INDEX_ERROR
    - LEXICAL_INDEX_ERROR
    - RERANKER_ERROR
    - ONLY_SOURCES_VIOLATION
    - LLM_PROVIDER_ERROR
    - VALIDATION_ERROR
    - RATE_LIMITED
    - INTERNAL_ERROR
- only_sources_verdict:
    - PASS
    - FAIL
- health_status:
    - ok
- embeddings_encoding_format:
    - float
- embeddings_response_object:
    - list

LIST_TABLES:
- tenants:
    - tenant_id (uuid)
    - tenant_key (string)
    - display_name (string)
    - is_active (boolean)
    - created_at (timestamp)
    - updated_at (timestamp)
- tenant_settings:
    - tenant_id (uuid)
    - citations_mode (enum)
    - only_sources_mode (enum)
    - default_prompt_template (string)
    - metadata_boost_profile (jsonb)
    - link_boost_profile (jsonb)
- groups:
    - group_id (string)
    - group_name (string)
- local_groups:
    - group_id (string)
    - group_name (string)
- tenant_group_bindings:
    - tenant_id (uuid)
    - group_id (string)
    - role (enum)
- users:
    - user_id (string)
    - principal_name (string)
    - display_name (string)
- user_groups:
    - user_id (string)
    - group_id (string)
- user_group_memberships:
    - user_id (string)
    - group_id (string)
- sources:
    - source_id (string)
    - tenant_id (uuid)
    - source_type (enum)
    - external_ref (string)
    - status (enum)
    - created_at (timestamp)
    - updated_at (timestamp)
- source_versions:
    - source_version_id (string)
    - source_id (string)
    - version_label (string)
    - checksum (string)
    - s3_raw_uri (string)
    - s3_markdown_uri (string)
    - metadata_json (jsonb)
    - discovered_at (timestamp)
- documents:
    - document_id (string)
    - tenant_id (uuid)
    - source_id (string)
    - source_version_id (string)
    - title (string)
    - author (string)
    - created_date (date)
    - updated_date (date)
    - space_key (string)
    - page_id (string)
    - parent_id (string)
    - url (string)
    - labels (jsonb)
- cross_links:
    - from_document_id (string)
    - to_document_id (string)
    - link_url (string)
    - link_type (enum)
- document_links:
    - from_document_id (string)
    - to_document_id (string)
    - link_url (string)
    - link_type (enum)
- chunks:
    - chunk_id (string)
    - document_id (string)
    - tenant_id (uuid)
    - chunk_path (string)
    - chunk_text (text)
    - token_count (integer)
    - ordinal (integer)
- chunk_fts:
    - chunk_id (string)
    - tenant_id (uuid)
    - fts_doc (tsvector)
- embeddings_refs:
    - chunk_id (string)
    - tenant_id (uuid)
    - embedding_model (string)
    - embedding (vector)
    - embedding_dim (integer)
- chunk_vectors:
    - chunk_id (string)
    - tenant_id (uuid)
    - embedding_model (string)
    - embedding (vector)
    - embedding_dim (integer)
- jobs:
    - job_id (string)
    - tenant_id (uuid)
    - job_type (enum)
    - job_status (enum)
    - requested_by (string)
    - started_at (timestamp)
    - finished_at (timestamp)
    - error_code (string)
    - error_message (string)
- ingest_jobs:
    - job_id (string)
    - tenant_id (uuid)
    - job_type (enum)
    - job_status (enum)
    - requested_by (string)
    - started_at (timestamp)
    - finished_at (timestamp)
    - error_code (string)
    - error_message (string)
- search_requests:
    - search_id (string)
    - tenant_id (uuid)
    - user_id (string)
    - query_text (text)
    - citations_requested (boolean)
- search_candidates:
    - search_id (string)
    - chunk_id (string)
    - lex_score (float)
    - vec_score (float)
    - rerank_score (float)
    - boosts_json (jsonb)
    - final_score (float)
    - rank_position (integer)
- answers:
    - answer_id (string)
    - search_id (string)
    - answer_text (text)
    - only_sources_verdict (enum)
    - citations_json (jsonb)
- logs:
    - event_id (string)
    - tenant_id (uuid)
    - correlation_id (uuid)
    - event_type (enum)
    - log_data_mode (enum)
    - payload_json (jsonb)
    - duration_ms (integer)
    - created_at (timestamp)
- event_logs:
    - event_id (string)
    - tenant_id (uuid)
    - correlation_id (uuid)
    - event_type (enum)
    - log_data_mode (enum)
    - payload_json (jsonb)
    - duration_ms (integer)
    - created_at (timestamp)
- pipeline_trace:
    - trace_id (string)
    - tenant_id (uuid)
    - correlation_id (uuid)
    - stage (enum)
    - status (enum)
    - started_at (timestamp)
    - ended_at (timestamp)
    - payload_json (jsonb)

LIST_ENV_VARS:
- DB_HOST
- DB_PORT
- DB_NAME
- DB_USER
- DB_PASSWORD
- DATABASE_URL
- PGVECTOR_ENABLED
- S3_ENDPOINT
- S3_ACCESS_KEY
- S3_SECRET_KEY
- S3_BUCKET_RAW
- S3_BUCKET_MARKDOWN
- S3_REGION
- S3_SECURE
- OLLAMA_BASE_URL
- OLLAMA_MODEL
- EMBEDDINGS_SERVICE_URL
- RAG_SERVICE_PORT
- EMBEDDINGS_SERVICE_PORT
- LOG_DATA_MODE
- RERANKER_MODEL
- RERANKER_TOP_K
- LLM_PROVIDER
- LLM_ENDPOINT
- LLM_MODEL
- LLM_API_KEY
- REQUEST_TIMEOUT_SECONDS
- EMBEDDINGS_TIMEOUT_SECONDS
- MAX_EMBED_BATCH_SIZE
- DEFAULT_TOP_K

LIST_JOB_STATUS:
- queued
- processing
- retrying
- done
- error
- canceled
- expired

LIST_ERROR_CODES:
- B-xxxx
- Q-xxxx
- W-xxxx
- S-xxxx
- AUTH_UNAUTHORIZED
- AUTH_FORBIDDEN_TENANT
- TENANT_NOT_FOUND
- SOURCE_NOT_FOUND
- SOURCE_FETCH_FAILED
- NORMALIZATION_FAILED
- CHUNKING_FAILED
- EMBEDDINGS_HTTP_ERROR
- EMBEDDINGS_TIMEOUT
- VECTOR_INDEX_ERROR
- LEXICAL_INDEX_ERROR
- RERANKER_ERROR
- ONLY_SOURCES_VIOLATION
- LLM_PROVIDER_ERROR
- VALIDATION_ERROR
- RATE_LIMITED
- INTERNAL_ERROR
ARCHITECTURE FROZEN
