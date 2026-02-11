# EPIC-08 / SP1 — Conversational Memory Data Model Contract

## Scope
This stop-point defines only storage primitives for conversational memory in `services/corporate-rag-service`.
No request/response API schema changes are included in SP1.

## Database objects
A new Alembic revision adds the following objects:

### Enums
- `conversation_status`: `active | archived`
- `conversation_role`: `user | assistant | system`
- `rewrite_strategy`: `none | llm_rewrite`

### Tables
1. `conversations`
   - `conversation_id` UUID PK
   - `tenant_id` UUID, indexed
   - `status` enum `conversation_status`
   - `created_at`, `last_active_at`

2. `conversation_turns`
   - `turn_id` UUID PK
   - `conversation_id` FK → `conversations.conversation_id`
   - `tenant_id` UUID, indexed
   - `turn_index` INT
   - `role` enum `conversation_role`
   - `text` TEXT
   - `created_at`
   - `meta` JSONB nullable
   - unique constraint: `(conversation_id, turn_index)`

3. `query_resolutions`
   - `resolution_id` UUID PK
   - `tenant_id` UUID, indexed
   - `conversation_id` UUID, indexed
   - `turn_id` FK → `conversation_turns.turn_id`, indexed
   - `resolved_query_text` TEXT
   - `rewrite_strategy` enum `rewrite_strategy`
   - `rewrite_inputs` JSONB nullable
   - `rewrite_confidence` FLOAT nullable
   - `topic_shift_detected` BOOL
   - `needs_clarification` BOOL
   - `clarification_question` TEXT nullable
   - `created_at`

4. `retrieval_trace_items`
   - Composite PK: `(tenant_id, conversation_id, turn_id, document_id, chunk_id, ordinal)`
   - Score fields: `score_lex_raw`, `score_vec_raw`, `score_rerank_raw`, `score_final` (FLOAT nullable)
   - `used_in_context`, `used_in_answer` (BOOL)
   - `citation_rank` INT nullable
   - `created_at`
   - indexes:
     - `(tenant_id, conversation_id, turn_id)`
     - `(tenant_id, conversation_id, created_at)`

5. `conversation_summaries`
   - Composite PK: `(tenant_id, conversation_id, summary_version)`
   - unique `(tenant_id, conversation_id, summary_version)`
   - `summary_text` TEXT
   - `covers_turn_index_to` INT
   - `created_at`

## ORM and repository contract
- SQLAlchemy models are added in `app/models/models.py` for each new table.
- `ConversationRepository` is added in `app/db/repositories.py`.
- Repository methods always include a tenant filter (`tenant_id == requested tenant`) to enforce tenant-safe access.

## Compatibility
- Existing endpoint behavior remains unchanged in SP1.
- No OpenAPI changes.
