# Data model

## app.documents
- document_id uuid PK
- source_type, source_ref, title, language
- content_text
- content_tsv (generated stored)
- embedding vector(1536) резерв

## logs.api_requests
Асинхронный data-plane лог.
