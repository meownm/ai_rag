from __future__ import annotations

import hashlib
import io
from pathlib import Path

from app.services.connectors.base import SourceItem


class FileByteIngestor:
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}

    def ingest_bytes(self, *, filename: str, payload: bytes) -> SourceItem:
        ext = Path(filename).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {ext}")

        markdown = self._to_markdown(ext, payload)
        digest = hashlib.sha256(payload).hexdigest()
        return SourceItem(
            source_type="FILE_UPLOAD_OBJECT",
            external_ref=digest,
            title=filename,
            markdown=markdown,
            url="",
            labels=["upload", ext.lstrip(".")],
        )

    def _to_markdown(self, ext: str, payload: bytes) -> str:
        if ext in {".txt", ".md"}:
            return payload.decode("utf-8", errors="ignore")
        if ext == ".docx":
            return self._docx_to_markdown(payload)
        if ext == ".pdf":
            return self._pdf_to_markdown(payload)
        raise ValueError(f"Unsupported file extension: {ext}")

    def _render_docx_table(self, table) -> list[str]:
        rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells] for row in table.rows]
        if not rows:
            return []
        header = rows[0]
        lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        return lines

    def _list_level(self, paragraph) -> int:
        p_pr = getattr(paragraph._p, "pPr", None)
        if p_pr is None or getattr(p_pr, "numPr", None) is None or getattr(p_pr.numPr, "ilvl", None) is None:
            return 0
        try:
            return int(p_pr.numPr.ilvl.val)
        except (TypeError, ValueError):
            return 0

    def _list_prefix(self, level: int) -> str:
        return "  " * max(level, 0)

    def _numfmt_for_level(self, paragraph, level: int) -> str | None:
        p_pr = getattr(paragraph._p, "pPr", None)
        if p_pr is None or getattr(p_pr, "numPr", None) is None or getattr(p_pr.numPr, "numId", None) is None:
            return None

        num_id = p_pr.numPr.numId.val
        numbering_part = getattr(paragraph.part, "numbering_part", None)
        if numbering_part is None:
            return None

        numbering_root = numbering_part.numbering_definitions._numbering
        num_nodes = numbering_root.xpath(f'.//w:num[@w:numId="{num_id}"]')
        if not num_nodes:
            return None

        abstract_num_id = num_nodes[0].xpath('./w:abstractNumId/@w:val')
        if not abstract_num_id:
            return None

        lvl_nodes = numbering_root.xpath(
            f'.//w:abstractNum[@w:abstractNumId="{abstract_num_id[0]}"]/w:lvl[@w:ilvl="{level}"]'
        )
        if not lvl_nodes:
            return None

        num_fmt = lvl_nodes[0].xpath('./w:numFmt/@w:val')
        return num_fmt[0] if num_fmt else None

    def _list_kind(self, paragraph, style: str, level: int) -> str | None:
        if "list bullet" in style:
            return "unordered"
        if "list number" in style:
            return "ordered"

        num_fmt = self._numfmt_for_level(paragraph, level)
        if num_fmt is None:
            return None
        if num_fmt in {"bullet", "none"}:
            return "unordered"
        return "ordered"

    def _paragraph_to_markdown(self, paragraph, numbered_index: int) -> tuple[str | None, int]:
        text = paragraph.text.strip()
        if not text:
            return None, numbered_index

        style = (paragraph.style.name or "").lower() if paragraph.style else ""
        if style.startswith("heading"):
            level = "".join(ch for ch in style if ch.isdigit()) or "1"
            return f"{'#' * max(1, int(level))} {text}", numbered_index

        list_level = self._list_level(paragraph)
        indentation = self._list_prefix(list_level)

        list_kind = self._list_kind(paragraph, style, list_level)
        if list_kind == "unordered":
            return f"{indentation}- {text}", numbered_index

        if list_kind == "ordered":
            numbered_index += 1
            return f"{indentation}{numbered_index}. {text}", numbered_index

        return text, numbered_index

    def _docx_to_markdown(self, payload: bytes) -> str:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        document = docx.Document(io.BytesIO(payload))
        lines: list[str] = []
        numbered_index = 0

        parent = document.element.body
        for child in parent.iterchildren():
            if child.tag.endswith("}p"):
                paragraph = Paragraph(child, document)
                rendered, numbered_index = self._paragraph_to_markdown(paragraph, numbered_index)
                if rendered:
                    lines.append(rendered)
                continue
            if child.tag.endswith("}tbl"):
                table = Table(child, document)
                lines.extend(self._render_docx_table(table))

        return "\n\n".join(lines)

    def _render_pdf_table(self, table: list[list[str | None]]) -> list[str]:
        rows = [[(cell or "").strip().replace("\n", " ") for cell in row] for row in table if row and any(cell for cell in row)]
        if len(rows) < 2:
            return []
        width = max(len(row) for row in rows)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        header = normalized[0]
        lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
        for row in normalized[1:]:
            lines.append("| " + " | ".join(row) + " |")
        return lines

    def _pdf_to_markdown(self, payload: bytes) -> str:
        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover - hard failure in misconfigured environments
            raise RuntimeError("pdfplumber is required for PDF ingestion") from exc

        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                blocks = [f"<!-- page:{idx} -->"]

                page_text = (page.extract_text() or "").strip()
                if page_text:
                    paragraphs = [part.strip() for part in page_text.split("\n\n") if part.strip()]
                    blocks.extend(paragraphs)

                for table in page.extract_tables() or []:
                    rendered = self._render_pdf_table(table)
                    if rendered:
                        blocks.extend(rendered)

                pages.append("\n\n".join(blocks))

        return "\n\n".join(page for page in pages if page.strip())
