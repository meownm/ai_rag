CREATE INDEX IF NOT EXISTS idx_documents_tsv ON app.documents USING GIN (content_tsv);
CREATE INDEX IF NOT EXISTS idx_documents_trgm ON app.documents USING GIN (content_text gin_trgm_ops);
