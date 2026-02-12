import io

import pytest

from app.services.file_ingestion import FileByteIngestor


def _set_list_level(paragraph, level: int) -> None:
    num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
    ilvl = num_pr.get_or_add_ilvl()
    ilvl.val = level


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


def test_ingest_docx_preserves_nested_bullet_lists():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    parent = doc.add_paragraph("Parent")
    parent.style = "List Bullet"
    _set_list_level(parent, 0)

    child = doc.add_paragraph("Child")
    child.style = "List Bullet"
    _set_list_level(child, 1)

    nested = doc.add_paragraph("Nested")
    nested.style = "List Bullet"
    _set_list_level(nested, 2)

    doc.save(stream)

    markdown = FileByteIngestor().ingest_bytes(filename="nested_bullet.docx", payload=stream.getvalue()).markdown
    assert "- Parent" in markdown
    assert "  - Child" in markdown
    assert "    - Nested" in markdown


def test_ingest_docx_preserves_nested_numbered_lists():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    root = doc.add_paragraph("Step 1")
    root.style = "List Number"
    _set_list_level(root, 0)

    sub = doc.add_paragraph("Step 1.1")
    sub.style = "List Number"
    _set_list_level(sub, 1)

    doc.save(stream)

    markdown = FileByteIngestor().ingest_bytes(filename="nested_numbered.docx", payload=stream.getvalue()).markdown
    assert "1. Step 1" in markdown
    assert "  1. Step 1.1" in markdown


def test_ingest_docx_preserves_three_level_nested_numbered_lists():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    l0 = doc.add_paragraph("L0")
    l0.style = "List Number"
    _set_list_level(l0, 0)
    l1 = doc.add_paragraph("L1")
    l1.style = "List Number"
    _set_list_level(l1, 1)
    l2 = doc.add_paragraph("L2")
    l2.style = "List Number"
    _set_list_level(l2, 2)

    doc.save(stream)
    markdown = FileByteIngestor().ingest_bytes(filename="three_nested_numbered.docx", payload=stream.getvalue()).markdown
    assert "1. L0" in markdown
    assert "  1. L1" in markdown
    assert "    1. L2" in markdown


def test_ingest_docx_preserves_three_level_nested_bullet_lists():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    l0 = doc.add_paragraph("L0")
    l0.style = "List Bullet"
    _set_list_level(l0, 0)
    l1 = doc.add_paragraph("L1")
    l1.style = "List Bullet"
    _set_list_level(l1, 1)
    l2 = doc.add_paragraph("L2")
    l2.style = "List Bullet"
    _set_list_level(l2, 2)

    doc.save(stream)
    markdown = FileByteIngestor().ingest_bytes(filename="three_nested_bullets.docx", payload=stream.getvalue()).markdown
    assert "- L0" in markdown
    assert "  - L1" in markdown
    assert "    - L2" in markdown


def test_ingest_docx_numbering_is_separate_per_list_level_and_numid():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    a1 = doc.add_paragraph("ListA-1")
    a1.style = "List Number"
    _set_list_level(a1, 0)
    a2 = doc.add_paragraph("ListA-2")
    a2.style = "List Number"
    _set_list_level(a2, 0)
    b1 = doc.add_paragraph("ListB-1")
    b1.style = "List Number"
    _set_list_level(b1, 1)

    doc.save(stream)
    markdown = FileByteIngestor().ingest_bytes(filename="numid_level_tracking.docx", payload=stream.getvalue()).markdown
    assert "1. ListA-1" in markdown
    assert "2. ListA-2" in markdown
    assert "  1. ListB-1" in markdown


def test_ingest_docx_preserves_mixed_nested_lists_structure():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    root = doc.add_paragraph("Root")
    root.style = "List Number"
    _set_list_level(root, 0)

    child = doc.add_paragraph("Child bullet")
    child.style = "List Bullet"
    _set_list_level(child, 1)

    doc.save(stream)

    markdown = FileByteIngestor().ingest_bytes(filename="mixed_nested.docx", payload=stream.getvalue()).markdown
    assert "1. Root" in markdown
    assert "  - Child bullet" in markdown


def test_ingest_docx_detects_numbering_from_numpr_when_style_is_plain():
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    doc = docx.Document()

    plain = doc.add_paragraph("Implicit numbered")
    plain.style = "List Number"
    _set_list_level(plain, 0)
    plain.style = "Normal"

    doc.save(stream)

    markdown = FileByteIngestor().ingest_bytes(filename="numpr_plain.docx", payload=stream.getvalue()).markdown
    assert "1. Implicit numbered" in markdown
