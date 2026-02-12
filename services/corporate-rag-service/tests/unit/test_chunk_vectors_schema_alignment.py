from pathlib import Path


def test_chunk_vectors_updated_at_guard_migration_is_idempotent_and_non_nullable():
    migration = Path("alembic/versions/0014_chunk_vectors_updated_at_integrity_guard.py").read_text(encoding="utf-8")
    assert "IF NOT EXISTS" in migration
    assert "ADD COLUMN updated_at" in migration
    assert "ALTER COLUMN updated_at SET DEFAULT now()" in migration
    assert "ALTER COLUMN updated_at SET NOT NULL" in migration


def test_chunk_vectors_upsert_references_existing_updated_at_column():
    ingestion = Path("app/services/ingestion.py").read_text(encoding="utf-8")
    model = Path("app/models/models.py").read_text(encoding="utf-8")

    assert "updated_at = now()" in ingestion
    assert "updated_at:" in model
    assert "server_default=func.now()" in model


def test_chunk_vectors_alignment_migration_enforces_composite_unique_index_and_updated_at_defaults():
    migration = Path("alembic/versions/0015_chunk_vectors_upsert_schema_alignment.py").read_text(encoding="utf-8")
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_chunk_vectors_tenant_chunk" in migration
    assert "ON chunk_vectors (tenant_id, chunk_id)" in migration
    assert "ALTER COLUMN updated_at SET DEFAULT now()" in migration
    assert "ALTER COLUMN updated_at SET NOT NULL" in migration


def test_chunk_vectors_upsert_conflict_target_matches_schema_constraint():
    ingestion = Path("app/services/ingestion.py").read_text(encoding="utf-8")
    assert "ON CONFLICT (tenant_id, chunk_id) DO UPDATE" in ingestion


def test_chunk_vectors_model_declares_composite_unique_constraint():
    model = Path("app/models/models.py").read_text(encoding="utf-8")
    assert 'UniqueConstraint("tenant_id", "chunk_id", name="uq_chunk_vectors_tenant_chunk")' in model
