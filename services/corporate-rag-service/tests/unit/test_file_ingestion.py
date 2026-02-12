import io

import pytest

from app.services.file_ingestion import FileByteIngestor


def test_ingest_txt_file():
    item = FileByteIngestor().ingest_bytes(filename="a.txt", payload=b"hello world")
    assert item.source_type == "FILE_UPLOAD_OBJECT"
    assert "hello world" in item.markdown


def test_ingest_docx_preserves_order_headings_and_lists():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()
    doc.add_heading("Title", level=1)
    doc.add_paragraph("Before table")

    bullet = doc.add_paragraph("first bullet")
    bullet.style = "List Bullet"

    numbered = doc.add_paragraph("first number")
    numbered.style = "List Number"

    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "h1"
    table.rows[0].cells[1].text = "h2"
    table.rows[1].cells[0].text = "v1"
    table.rows[1].cells[1].text = "v2"

    doc.add_paragraph("After table")
    doc.save(stream)

    item = FileByteIngestor().ingest_bytes(filename="a.docx", payload=stream.getvalue())
    markdown = item.markdown
    assert "# Title" in markdown
    assert "- first bullet" in markdown
    assert "1. first number" in markdown
    assert markdown.index("Before table") < markdown.index("| h1 | h2 |") < markdown.index("After table")


def test_ingest_pdf_contains_page_markers_and_table(monkeypatch):
    import sys
    import types
    class FakePage:
        def extract_text(self):
            return "paragraph one\n\nparagraph two"

        def extract_tables(self):
            return [[["c1", "c2"], ["v1", "v2"]]]

    class FakePdf:
        def __init__(self):
            self.pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda *_args, **_kwargs: FakePdf())
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)
    item = FileByteIngestor().ingest_bytes(filename="a.pdf", payload=b"%PDF")
    assert "<!-- page:1 -->" in item.markdown
    assert "paragraph two" in item.markdown
    assert "| c1 | c2 |" in item.markdown


def test_ingest_pdf_requires_pdfplumber_negative(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "pdfplumber":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    with pytest.raises(RuntimeError, match="pdfplumber is required"):
        FileByteIngestor().ingest_bytes(filename="a.pdf", payload=b"%PDF")


def test_ingest_unsupported_extension_raises():
    with pytest.raises(ValueError):
        FileByteIngestor().ingest_bytes(filename="a.xlsx", payload=b"123")
