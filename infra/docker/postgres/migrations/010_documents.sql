CREATE TABLE IF NOT EXISTS app.documents (
  document_id uuid PRIMARY KEY,
  source_type text NOT NULL,
  source_ref text,
  title text,
  language text,
  content_text text NOT NULL,
  content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', unaccent(content_text))) STORED,
  embedding vector(1536),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz
);
