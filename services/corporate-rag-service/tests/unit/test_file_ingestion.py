import io

import pytest

from app.services.file_ingestion import FileByteIngestor


def test_ingest_txt_file():
    item = FileByteIngestor().ingest_bytes(filename="a.txt", payload=b"hello world")
    assert item.source_type == "FILE_UPLOAD_OBJECT"
    assert "hello world" in item.markdown


def test_ingest_docx_keeps_headings_and_table():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()
    doc.add_heading("Title", level=1)
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "h1"
    table.rows[0].cells[1].text = "h2"
    table.rows[1].cells[0].text = "v1"
    table.rows[1].cells[1].text = "v2"
    doc.save(stream)

    item = FileByteIngestor().ingest_bytes(filename="a.docx", payload=stream.getvalue())
    assert "# Title" in item.markdown
    assert "| h1 | h2 |" in item.markdown


def test_ingest_pdf_contains_page_markers(monkeypatch):
    class FakePage:
        def __init__(self, txt):
            self.txt = txt

        def extract_text(self):
            return self.txt

    class FakeReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = [FakePage("page one"), FakePage("page two")]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)
    item = FileByteIngestor().ingest_bytes(filename="a.pdf", payload=b"%PDF")
    assert "<!-- page:1 -->" in item.markdown
    assert "page two" in item.markdown


def test_ingest_unsupported_extension_raises():
    with pytest.raises(ValueError):
        FileByteIngestor().ingest_bytes(filename="a.xlsx", payload=b"123")
