# Pipeline Trace

This file will be expanded as epics are implemented.

## Planned pipeline
1. Upload / register document
2. Store raw in MinIO
3. Extract text (PDF/DOCX/DOC/TXT)
4. Normalize text
5. Persist text + metadata in PostgreSQL
6. Chunk text
7. Embed chunks into vectors
8. Index/update vector store (pgvector)
9. Full-text index update
10. Query:
   - FTS retrieval
   - vector retrieval
   - hybrid merge + ranking
11. RAG synthesis (structured output only)
12. Return response + provenance (document IDs, chunk IDs, scores)
