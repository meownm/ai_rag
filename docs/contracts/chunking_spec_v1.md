# Chunking Specification v1

Status: **NORMATIVE**
Version: **v1**

## 1. Purpose
This specification defines deterministic chunking rules for ingestion so retrieval, scoring, and citations are stable across re-indexes.

## 2. Input and normalization contract
1. Input to chunking MUST be normalized Markdown produced by the `NORMALIZE_MARKDOWN` pipeline stage.
2. UTF-8 decoding errors MUST fail the source with `CHUNKING_FAILED`.
3. Line endings MUST be normalized to `\n`.
4. Excess horizontal whitespace inside lines SHOULD be collapsed, except inside fenced code blocks and tables.

## 3. Structural parsing
Chunking MUST preserve source structure and extract the following parse tree nodes in order:
- headings (`#`..`######`)
- paragraphs
- bullet/ordered list blocks
- tables
- fenced code blocks
- block quotes

For each emitted chunk, `headings_path` MUST contain the active heading stack in document order.

## 4. Chunk boundaries
1. A new chunk MUST start when any of the following occurs:
   - heading level changes
   - table starts/ends
   - fenced code block starts/ends
   - list context switches between ordered/unordered or exits
   - size threshold reached (see §5)
2. Adjacent short paragraphs under identical heading path MAY be merged.
3. Chunks MUST NOT mix content from different documents or source versions.

## 5. Size policy
- Target size: **350 tokens**.
- Soft max: **450 tokens**.
- Hard max: **520 tokens**.

Rules:
1. While appending structural units, stop at soft max and emit.
2. If a single structural unit exceeds hard max, split by sentence boundaries.
3. If sentence splitting still exceeds hard max, split by token windows with 15% overlap.

## 6. Overlap policy
- Default overlap between neighboring chunks: **15% tokens**.
- Overlap MUST preserve sentence boundaries when possible.
- Overlap MUST NOT cross heading boundaries unless needed to satisfy minimum context for citations.

## 7. Stable identifiers
`chunk_id` MUST be deterministic and stable for unchanged content:

```
chunk_id = sha256(
  tenant_id + "|" + document_id + "|" + source_version_id + "|" +
  ordinal + "|" + canonical_chunk_text
)
```

Where `canonical_chunk_text` is normalized text with collapsed internal whitespace (outside code/table literals).

## 8. Required metadata per chunk
Each chunk record MUST include:
- `chunk_id`
- `tenant_id`
- `document_id`
- `ordinal`
- `chunk_path` (serialized heading/list/table path)
- `headings_path` (array form)
- `token_count`
- `chunk_text`

## 9. Link extraction requirement
Confluence links discovered during parse MUST be emitted into link artifacts and later persisted to `document_links`/`cross_links` mapping with:
- source document
- resolved target document if available
- original URL
- link type

## 10. Determinism and re-index behavior
Given identical normalized markdown and metadata, chunking output MUST be byte-for-byte reproducible for:
- chunk order
- chunk boundaries
- chunk ids
- token counts (for fixed tokenizer version)

## 11. Validation checklist
A chunking run is valid only if all are true:
- no emitted chunk exceeds hard max
- no chunk has empty text
- ordinals are contiguous starting at 0
- heading path is present for non-root chunks
- stable-id formula applied

## 12. Backward compatibility
This is `v1`. Any breaking rule change MUST create `chunking_spec_v2.md` and migration notes.
