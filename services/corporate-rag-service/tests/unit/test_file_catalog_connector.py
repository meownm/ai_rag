from pathlib import Path

from app.services.connectors.base import SyncContext
from app.services.connectors.file_catalog import FileCatalogConnector


def test_fcs_sp1_local_descriptors_deterministic_order_and_windows_safe(monkeypatch, tmp_path: Path):
    root = tmp_path / "root"
    (root / "b").mkdir(parents=True)
    (root / "a").mkdir(parents=True)
    (root / "b" / "z.TXT").write_text("b")
    (root / "a" / "x.md").write_text("a")

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".txt,.md")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    descriptors = connector.list_descriptors("t1", SyncContext(max_items_per_run=100, page_size=10, incremental_enabled=True))
    refs = [d.external_ref for d in descriptors]
    assert refs == sorted(refs)
    assert refs == ["fs:a/x.md", "fs:b/z.TXT"]
    assert all("\\" not in d.external_ref for d in descriptors)


def test_fcs_sp1_oversize_file_skipped(monkeypatch, tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    big = root / "large.txt"
    big.write_bytes(b"a" * 2048)

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".txt")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 0)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    descriptors = connector.list_descriptors("t1", SyncContext(max_items_per_run=100, page_size=10, incremental_enabled=True))
    assert descriptors == []


def test_fcs_sp4_local_fetch_builds_metadata_positive(monkeypatch, tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    p = root / "doc.md"
    p.write_text("# t")

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".md")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    descriptor = connector.list_descriptors("t1", SyncContext(max_items_per_run=10, page_size=10, incremental_enabled=True))[0]
    result = connector.fetch_item("t1", descriptor)
    assert result.error is None
    assert result.item is not None
    assert result.item.metadata["source"] == "fs"
    assert result.item.metadata["rel_path"] == "doc.md"


def test_fcs_sp4_local_fetch_negative_empty_markdown(monkeypatch, tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    p = root / "doc.md"
    p.write_text("# t")

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".md")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    descriptor = connector.list_descriptors("t1", SyncContext(max_items_per_run=10, page_size=10, incremental_enabled=True))[0]

    class EmptyIngestor:
        def ingest_bytes(self, *, filename: str, payload: bytes):
            from app.services.connectors.base import SourceItem

            return SourceItem(source_type="FILE_UPLOAD_OBJECT", external_ref="x", title=filename, markdown="   ")

    connector._ingestor = EmptyIngestor()
    result = connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "F-EMPTY-MARKDOWN"


def test_fcs_sp7_symlink_escape_rejected(monkeypatch, tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    link = root / "link.txt"

    try:
        link.symlink_to(outside)
    except OSError:
        return

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".txt")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    descriptors = connector.list_descriptors("t1", SyncContext(max_items_per_run=100, page_size=10, incremental_enabled=True))
    assert descriptors == []


def test_fcs_sp7_fetch_rejects_path_escape(monkeypatch, tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# x")

    from app.services.connectors import file_catalog as module
    from app.services.connectors.base import SourceDescriptor

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".md")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    descriptor = SourceDescriptor(source_type="FILE_CATALOG_OBJECT", external_ref="fs:outside.md", title="outside.md", metadata={"abs_path": str(outside)})
    result = connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "F-SEC-SYMLINK-ESCAPE"


def test_fcs_sp9_respects_cap_and_logs_summary(monkeypatch, tmp_path: Path, caplog):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.md").write_text("a")
    (root / "b.md").write_text("b")

    from app.services.connectors import file_catalog as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ROOT_PATH", str(root))
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_RECURSIVE", True)
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_ALLOWED_EXTENSIONS", ".md")
    monkeypatch.setattr(fake_settings, "FILE_CATALOG_MAX_FILE_MB", 50)
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = FileCatalogConnector()
    with caplog.at_level("INFO"):
        descriptors = connector.list_descriptors("t1", SyncContext(max_items_per_run=1, page_size=10, incremental_enabled=True))

    assert len(descriptors) == 1
    assert "file_catalog_summary" in caplog.text
