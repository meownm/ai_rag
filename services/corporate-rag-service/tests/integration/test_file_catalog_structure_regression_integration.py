import uuid
from pathlib import Path

from app.services.connectors.base import SourceItem
from app.services.connectors.file_catalog import FileCatalogConnector
from app.services.ingestion import ingest_sources_sync
from tests.unit.test_ingestion_pipeline import FakeDb, FakeStorage


def test_fcs_sp8_structured_regression_no_duplicates(monkeypatch, tmp_path: Path):
    root = tmp_path / "fixtures"
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "a.docx").write_bytes(b"fake-docx")
    (root / "nested" / "b.pdf").write_bytes(b"fake-pdf")
    (root / "c.txt").write_text("plain text")
    (root / "d.md").write_text("# Heading\n\n- Item")

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".pdf,.docx,.txt,.md")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    class FakeByteIngestor:
        def ingest_bytes(self, *, filename: str, payload: bytes) -> SourceItem:
            ext = Path(filename).suffix.lower()
            if ext == ".docx":
                md = "# Docx Title\n\n1. First\n   - Sub\n\n| C1 | C2 |\n| --- | --- |\n| v1 | v2 |"
            elif ext == ".pdf":
                md = "# Pdf Title\n\n| K | V |\n| --- | --- |\n| alpha | beta |"
            elif ext == ".txt":
                md = "txt body"
            else:
                md = "# Md Title\n\n- md item"
            return SourceItem(source_type="FILE_UPLOAD_OBJECT", external_ref=filename, title=filename, markdown=md)

    connector = FileCatalogConnector()
    connector._ingestor = FakeByteIngestor()

    class FakeRegistry:
        def get(self, source_type):
            return connector

    class FakeEmbeddingsClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def embed_texts(self, texts, **_kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

    db = FakeDb()
    storage = FakeStorage()
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")

    monkeypatch.setattr("app.services.ingestion.register_default_connectors", lambda: FakeRegistry())
    monkeypatch.setattr("app.services.ingestion.EmbeddingsClient", FakeEmbeddingsClient)

    first = ingest_sources_sync(db, tenant, ["FILE_CATALOG_OBJECT"], storage=storage)
    second = ingest_sources_sync(db, tenant, ["FILE_CATALOG_OBJECT"], storage=storage)

    assert first["documents"] == 4
    assert second["documents"] == 0

    chunk_values = "\n".join(str(v) for v in db.chunk_texts.values())
    assert "md item" in chunk_values
    assert "alpha" in chunk_values
