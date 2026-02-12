from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from app.services.connectors.base import ConnectorError, ConnectorFetchResult, SourceConnector, SourceDescriptor, SourceItem, SyncContext
from app.services.file_ingestion import FileByteIngestor

AC_NS = "http://atlassian.com/content"
RI_NS = "http://atlassian.com/resource/identifier"


def _load_settings() -> Any:
    try:
        from app.core.config import settings

        return settings
    except Exception:  # noqa: BLE001
        return SimpleNamespace(
            CONFLUENCE_BASE_URL="",
            CONFLUENCE_AUTH_MODE="pat",
            CONFLUENCE_PAT="",
            CONFLUENCE_USERNAME="",
            CONFLUENCE_PASSWORD="",
            CONFLUENCE_REQUEST_TIMEOUT_SECONDS=30,
            CONFLUENCE_CQL="",
            CONFLUENCE_SPACE_KEYS="",
            CONFLUENCE_FETCH_BODY_REPRESENTATION="storage",
        )


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _norm_text(value: str) -> str:
    return " ".join(value.split())


def _extract_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return _norm_text("".join(node.itertext()))


def _sanitize_storage_xhtml(storage_xhtml: str) -> str:
    cleaned = re.sub(r"<\s*(script|style)\b[^>]*>.*?<\s*/\s*\1\s*>", "", storage_xhtml, flags=re.IGNORECASE | re.DOTALL)
    return cleaned


def _render_table_markdown(table: ET.Element) -> str:
    rows: list[list[tuple[str, int, int, bool]]] = []
    for tr in table.findall(".//tr"):
        row: list[tuple[str, int, int, bool]] = []
        for cell in tr:
            name = _local_name(cell.tag)
            if name not in {"td", "th"}:
                continue
            text = _extract_text(cell)
            colspan = max(1, int(cell.attrib.get("colspan", "1") or "1"))
            rowspan = max(1, int(cell.attrib.get("rowspan", "1") or "1"))
            is_header = name == "th"
            row.append((text, colspan, rowspan, is_header))
        if row:
            rows.append(row)

    if not rows:
        return ""

    expanded: list[list[str]] = []
    pending_rowspans: dict[int, tuple[str, int]] = {}
    header_row_idx = 0 if any(cell[3] for cell in rows[0]) else -1

    for row_idx, row in enumerate(rows):
        rendered: list[str] = []
        col = 0
        while col in pending_rowspans:
            text, rem = pending_rowspans[col]
            rendered.append(text)
            if rem > 1:
                pending_rowspans[col] = (text, rem - 1)
            else:
                del pending_rowspans[col]
            col += 1

        only_headers = True
        for text, colspan, rowspan, is_header in row:
            only_headers = only_headers and is_header
            for _ in range(colspan):
                rendered.append(text)
                if rowspan > 1:
                    pending_rowspans[col] = (text, rowspan - 1)
                col += 1
        if row_idx == 0 and only_headers:
            header_row_idx = 0
        expanded.append(rendered)

    width = max(len(r) for r in expanded)
    norm_rows = [r + [""] * (width - len(r)) for r in expanded]
    if header_row_idx < 0:
        header = [f"Column {idx + 1}" for idx in range(width)]
        data_rows = norm_rows
    else:
        header = norm_rows[header_row_idx]
        data_rows = norm_rows[header_row_idx + 1 :]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in data_rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _extract_attachment_filename(node: ET.Element | None) -> str:
    if node is None:
        return "attachment"
    filename = node.attrib.get(f"{{{RI_NS}}}filename") or node.attrib.get("ri:filename")
    return filename or "attachment"


def _extension_from_media_type(media_type: str | None) -> str:
    mapping = {
        "text/plain": ".txt",
        "text/markdown": ".md",
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    if not media_type:
        return ""
    return mapping.get(media_type.lower().strip(), "")


def _render_inline(node: ET.Element | None) -> str:
    if node is None:
        return ""

    parts: list[str] = []
    if node.text:
        parts.append(node.text)

    for child in list(node):
        local = _local_name(child.tag)
        if local == "link":
            attachment = child.find(f".//{{{RI_NS}}}attachment")
            if attachment is not None:
                filename = _extract_attachment_filename(attachment)
                label = _norm_text(_extract_text(child)) or filename
                parts.append(f"[{label}](attachment:{filename})")
            else:
                href = child.attrib.get("href") or child.attrib.get("ri:value") or ""
                label = _norm_text(_extract_text(child)) or href
                parts.append(f"[{label}]({href})" if href else label)
        elif local == "structured-macro":
            parts.append(_render_macro(child).strip())
        elif local == "attachment":
            filename = _extract_attachment_filename(child)
            parts.append(f"[attachment](attachment:{filename})")
        else:
            parts.append(_render_inline(child))
        if child.tail:
            parts.append(child.tail)

    return _norm_text(html.unescape("".join(parts)))


def _render_code_block(code: str, language: str = "") -> str:
    lang = language.strip()
    fence = f"```{lang}" if lang else "```"
    return f"{fence}\n{code.rstrip()}\n```"


def _macro_parameter(macro: ET.Element, name: str) -> str:
    for child in list(macro):
        if _local_name(child.tag) == "parameter" and child.attrib.get(f"{{{AC_NS}}}name") == name:
            return _extract_text(child)
    return ""


def _render_macro(macro: ET.Element) -> str:
    macro_name = macro.attrib.get(f"{{{AC_NS}}}name") or macro.attrib.get("ac:name") or ""
    macro_name = macro_name.strip().lower()

    if macro_name == "code":
        language = _macro_parameter(macro, "language")
        body = macro.find(f".//{{{AC_NS}}}plain-text-body")
        code_text = "".join(body.itertext()) if body is not None else _extract_text(macro)
        return _render_code_block(code_text, language)

    if macro_name in {"info", "note"}:
        body = macro.find(f".//{{{AC_NS}}}rich-text-body")
        content = _render_blocks(body) if body is not None else _extract_text(macro)
        label = macro_name.upper()
        lines = [line for line in content.splitlines() if line.strip()]
        if not lines:
            return f"> **{label}:**"
        return "\n".join([f"> **{label}:** {lines[0]}", *[f"> {line}" for line in lines[1:]]])

    if macro_name == "expand":
        title = _macro_parameter(macro, "title") or "Expand"
        body = macro.find(f".//{{{AC_NS}}}rich-text-body")
        content = _render_blocks(body) if body is not None else _extract_text(macro)
        lines = [f"#### {title}"]
        if content.strip():
            lines.append(content.strip())
        return "\n\n".join(lines)

    return f"[macro:{macro_name}]"


def _render_list(list_node: ET.Element, depth: int = 0) -> list[str]:
    ordered = _local_name(list_node.tag) == "ol"
    lines: list[str] = []
    index = 1
    for li in [child for child in list(list_node) if _local_name(child.tag) == "li"]:
        prefix = f"{index}. " if ordered else "- "
        indent = "  " * depth
        inline_parts: list[str] = []
        nested_blocks: list[str] = []

        if li.text and li.text.strip():
            inline_parts.append(_norm_text(li.text))

        for child in list(li):
            local = _local_name(child.tag)
            if local in {"ul", "ol"}:
                nested_blocks.extend(_render_list(child, depth + 1))
            elif local == "structured-macro":
                nested_blocks.extend(_render_macro(child).splitlines())
            elif local == "table":
                nested_blocks.extend(_render_table_markdown(child).splitlines())
            else:
                inline_parts.append(_render_inline(child))
            if child.tail and child.tail.strip():
                inline_parts.append(_norm_text(child.tail))

        line_text = _norm_text(" ".join(part for part in inline_parts if part))
        lines.append(f"{indent}{prefix}{line_text}".rstrip())
        lines.extend(nested_blocks)
        if ordered:
            index += 1

    return lines


def _render_blocks(root: ET.Element | None) -> str:
    if root is None:
        return ""

    lines: list[str] = []

    for child in list(root):
        local = _local_name(child.tag)
        if local in {"script", "style"}:
            continue

        if local in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(local[1])
            lines.append(f"{'#' * level} {_render_inline(child)}".rstrip())
            lines.append("")
            continue

        if local == "p":
            text = _render_inline(child)
            if text:
                lines.append(text)
                lines.append("")
            continue

        if local in {"ul", "ol"}:
            lines.extend(_render_list(child, depth=0))
            lines.append("")
            continue

        if local == "table":
            table = _render_table_markdown(child)
            if table:
                lines.extend(table.splitlines())
                lines.append("")
            continue

        if local == "pre":
            code_node = next((n for n in list(child) if _local_name(n.tag) == "code"), None)
            code_text = "".join(code_node.itertext()) if code_node is not None else "".join(child.itertext())
            language = ""
            if code_node is not None:
                language = code_node.attrib.get("data-language", "") or code_node.attrib.get("class", "").replace("language-", "")
            lines.append(_render_code_block(code_text, language))
            lines.append("")
            continue

        if local == "structured-macro":
            lines.append(_render_macro(child))
            lines.append("")
            continue

        if local == "link":
            lines.append(_render_inline(child))
            lines.append("")
            continue

        text = _render_inline(child)
        if text:
            lines.append(text)
            lines.append("")

    while lines and not lines[-1].strip():
        lines.pop()
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def storage_html_to_markdown(storage_xhtml: str) -> str:
    cleaned = _sanitize_storage_xhtml(storage_xhtml)
    wrapped = f'<root xmlns:ac="{AC_NS}" xmlns:ri="{RI_NS}">{cleaned}</root>'
    try:
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        fallback = re.sub(r"<[^>]+>", "", cleaned)
        return _norm_text(fallback)
    return _render_blocks(root)


@dataclass
class ConfluenceClient:
    base_url: str
    auth_mode: str
    pat: str
    username: str
    password: str
    timeout_seconds: int = 30

    def _auth_headers(self) -> dict[str, str]:
        if self.auth_mode == "pat" and self.pat:
            return {"Authorization": f"Bearer {self.pat}"}
        if self.auth_mode == "basic" and self.username:
            encoded = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            return {"Authorization": f"Basic {encoded}"}
        return {}

    def list_pages(self, *, cql: str, start: int, limit: int) -> list[dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/rest/api/content/search"
        with httpx.Client(timeout=self.timeout_seconds, headers=self._auth_headers()) as client:
            response = client.get(url, params={"cql": cql, "start": start, "limit": limit})
            response.raise_for_status()
            payload = response.json()
        return payload.get("results", [])

    def fetch_page_body_by_id(self, page_id: str, *, representation: str) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/rest/api/content/{page_id}"
        expand = f"body.{representation},version,history"
        with httpx.Client(timeout=self.timeout_seconds, headers=self._auth_headers()) as client:
            response = client.get(url, params={"expand": expand})
            response.raise_for_status()
            return response.json()

    def list_attachments(self, *, cql: str, start: int, limit: int) -> list[dict[str, Any]]:
        url = f"{self.base_url.rstrip('/')}/rest/api/content/search"
        with httpx.Client(timeout=self.timeout_seconds, headers=self._auth_headers()) as client:
            response = client.get(url, params={"cql": cql, "start": start, "limit": limit})
            response.raise_for_status()
            payload = response.json()
        return payload.get("results", [])

    def fetch_attachment_by_id(self, attachment_id: str) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/rest/api/content/{attachment_id}"
        with httpx.Client(timeout=self.timeout_seconds, headers=self._auth_headers()) as client:
            response = client.get(url, params={"expand": "version,container,_links,metadata"})
            response.raise_for_status()
            return response.json()

    def download_attachment(self, download_url: str) -> bytes:
        if download_url.startswith("http://") or download_url.startswith("https://"):
            url = download_url
        else:
            url = f"{self.base_url.rstrip('/')}/{download_url.lstrip('/')}"
        with httpx.Client(timeout=self.timeout_seconds, headers=self._auth_headers()) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content


class ConfluencePagesConnector(SourceConnector):
    source_type = "CONFLUENCE_PAGE"

    def __init__(self, client: ConfluenceClient | None = None) -> None:
        cfg = _load_settings()
        self.client = client or ConfluenceClient(
            base_url=cfg.CONFLUENCE_BASE_URL,
            auth_mode=cfg.CONFLUENCE_AUTH_MODE,
            pat=cfg.CONFLUENCE_PAT,
            username=cfg.CONFLUENCE_USERNAME,
            password=cfg.CONFLUENCE_PASSWORD,
            timeout_seconds=cfg.CONFLUENCE_REQUEST_TIMEOUT_SECONDS,
        )

    def is_configured(self) -> tuple[bool, str | None]:
        cfg = _load_settings()
        if not cfg.CONFLUENCE_BASE_URL:
            return False, "CONFLUENCE_BASE_URL is not configured"
        if cfg.CONFLUENCE_AUTH_MODE == "pat" and not cfg.CONFLUENCE_PAT:
            return False, "CONFLUENCE_PAT is required for pat auth"
        return True, None

    def _build_cql(self) -> str:
        cfg = _load_settings()
        if cfg.CONFLUENCE_CQL:
            return cfg.CONFLUENCE_CQL
        if cfg.CONFLUENCE_SPACE_KEYS:
            keys = [k.strip() for k in cfg.CONFLUENCE_SPACE_KEYS.split(",") if k.strip()]
            if keys:
                return "type=page and space in (" + ",".join(f'"{k}"' for k in keys) + ")"
        return "type=page"

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        cql = self._build_cql()
        out: list[SourceDescriptor] = []
        start = 0
        while len(out) < sync_context.max_items_per_run:
            page = self.client.list_pages(cql=cql, start=start, limit=sync_context.page_size)
            if not page:
                break
            for entry in page:
                page_id = str(entry.get("id") or "")
                if not page_id:
                    continue
                title = str(entry.get("title") or page_id)
                space_key = ((entry.get("space") or {}).get("key") if isinstance(entry.get("space"), dict) else None) or ""
                history = entry.get("history") if isinstance(entry.get("history"), dict) else {}
                version = entry.get("version") if isinstance(entry.get("version"), dict) else {}
                last_modified = _parse_dt(
                    (history.get("lastUpdated") or {}).get("when") if isinstance(history.get("lastUpdated"), dict) else version.get("when")
                )
                out.append(
                    SourceDescriptor(
                        source_type=self.source_type,
                        external_ref=f"page:{page_id}",
                        title=title,
                        last_modified=last_modified,
                        checksum_hint=f"v:{version.get('number')}" if version.get("number") is not None else None,
                        metadata={"page_id": page_id, "spaceKey": space_key},
                    )
                )
                if len(out) >= sync_context.max_items_per_run:
                    break
            start += sync_context.page_size
        return out

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        cfg = _load_settings()
        page_id = str(descriptor.metadata.get("page_id") or descriptor.external_ref.replace("page:", ""))
        try:
            payload = self.client.fetch_page_body_by_id(page_id, representation=cfg.CONFLUENCE_FETCH_BODY_REPRESENTATION)
        except httpx.HTTPError as exc:
            return ConnectorFetchResult(error=ConnectorError("C-FETCH-FAILED", str(exc), retryable=True))

        body = payload.get("body") or {}
        rep = body.get(cfg.CONFLUENCE_FETCH_BODY_REPRESENTATION) or {}
        value = str(rep.get("value") or "")
        markdown = storage_html_to_markdown(value)
        if not markdown.strip():
            return ConnectorFetchResult(error=ConnectorError("C-EMPTY-BODY", f"Empty body for page:{page_id}"))

        links = payload.get("_links") if isinstance(payload.get("_links"), dict) else {}
        webui = links.get("webui") or ""
        base = links.get("base") or cfg.CONFLUENCE_BASE_URL.rstrip("/")
        url = f"{base}{webui}" if webui else ""
        version = payload.get("version") if isinstance(payload.get("version"), dict) else {}
        last_modified = _parse_dt(version.get("when"))

        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=str(payload.get("title") or descriptor.title),
                markdown=markdown,
                url=url,
                metadata={
                    "spaceKey": descriptor.metadata.get("spaceKey"),
                    "webui": webui,
                    "version": version.get("number"),
                    "lastModified": last_modified.isoformat() if last_modified else None,
                },
            )
        )


class ConfluenceAttachmentConnector(SourceConnector):
    source_type = "CONFLUENCE_ATTACHMENT"

    def __init__(self, client: ConfluenceClient | None = None, file_ingestor: FileByteIngestor | None = None) -> None:
        cfg = _load_settings()
        self.client = client or ConfluenceClient(
            base_url=cfg.CONFLUENCE_BASE_URL,
            auth_mode=cfg.CONFLUENCE_AUTH_MODE,
            pat=cfg.CONFLUENCE_PAT,
            username=cfg.CONFLUENCE_USERNAME,
            password=cfg.CONFLUENCE_PASSWORD,
            timeout_seconds=cfg.CONFLUENCE_REQUEST_TIMEOUT_SECONDS,
        )
        self.file_ingestor = file_ingestor or FileByteIngestor()

    def is_configured(self) -> tuple[bool, str | None]:
        cfg = _load_settings()
        if not cfg.CONFLUENCE_BASE_URL:
            return False, "CONFLUENCE_BASE_URL is not configured"
        if cfg.CONFLUENCE_AUTH_MODE == "pat" and not cfg.CONFLUENCE_PAT:
            return False, "CONFLUENCE_PAT is required for pat auth"
        return True, None

    def _build_cql(self) -> str:
        cfg = _load_settings()
        if cfg.CONFLUENCE_CQL:
            return f"type=attachment and ({cfg.CONFLUENCE_CQL})"
        if cfg.CONFLUENCE_SPACE_KEYS:
            keys = [k.strip() for k in cfg.CONFLUENCE_SPACE_KEYS.split(",") if k.strip()]
            if keys:
                return "type=attachment and space in (" + ",".join(f'\"{k}\"' for k in keys) + ")"
        return "type=attachment"

    def list_descriptors(self, tenant_id: str, sync_context: SyncContext) -> list[SourceDescriptor]:
        cql = self._build_cql()
        out: list[SourceDescriptor] = []
        start = 0
        while len(out) < sync_context.max_items_per_run:
            page = self.client.list_attachments(cql=cql, start=start, limit=sync_context.page_size)
            if not page:
                break
            for entry in page:
                attachment_id = str(entry.get("id") or "")
                if not attachment_id:
                    continue
                container = entry.get("container") if isinstance(entry.get("container"), dict) else {}
                container_id = str(container.get("id") or "")
                version = entry.get("version") if isinstance(entry.get("version"), dict) else {}
                last_modified = _parse_dt(version.get("when"))
                metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
                media_type = metadata.get("mediaType") or ""
                out.append(
                    SourceDescriptor(
                        source_type=self.source_type,
                        external_ref=f"attachment:{attachment_id}",
                        title=str(entry.get("title") or attachment_id),
                        last_modified=last_modified,
                        checksum_hint=f"v:{version.get('number')}" if version.get("number") is not None else None,
                        metadata={"attachment_id": attachment_id, "container_id": container_id, "media_type": media_type},
                    )
                )
                if len(out) >= sync_context.max_items_per_run:
                    break
            start += sync_context.page_size
        return out

    def fetch_item(self, tenant_id: str, descriptor: SourceDescriptor) -> ConnectorFetchResult:
        attachment_id = str(descriptor.metadata.get("attachment_id") or descriptor.external_ref.replace("attachment:", ""))
        try:
            payload = self.client.fetch_attachment_by_id(attachment_id)
            links = payload.get("_links") if isinstance(payload.get("_links"), dict) else {}
            download = str(links.get("download") or "")
            if not download:
                return ConnectorFetchResult(error=ConnectorError("C-ATTACHMENT-MISSING-DOWNLOAD", f"No download URL for attachment:{attachment_id}"))
            raw_bytes = self.client.download_attachment(download)
        except httpx.HTTPError as exc:
            return ConnectorFetchResult(error=ConnectorError("C-ATTACHMENT-FETCH-FAILED", str(exc), retryable=True))

        filename = str(payload.get("title") or descriptor.title or f"{attachment_id}.bin")
        suffix = Path(filename).suffix.lower()
        if suffix not in FileByteIngestor.SUPPORTED_EXTENSIONS:
            media_type = (payload.get("metadata") or {}).get("mediaType") if isinstance(payload.get("metadata"), dict) else None
            inferred = _extension_from_media_type(media_type)
            if inferred and inferred in FileByteIngestor.SUPPORTED_EXTENSIONS:
                base_name = Path(filename).stem if suffix else filename
                filename = f"{base_name}{inferred}"
                suffix = inferred
            else:
                return ConnectorFetchResult(
                    error=ConnectorError("C-ATTACHMENT-UNSUPPORTED-TYPE", f"Unsupported attachment extension: {suffix or '<none>'}")
                )

        try:
            converted = self.file_ingestor.ingest_bytes(filename=filename, payload=raw_bytes)
        except (ValueError, RuntimeError) as exc:
            return ConnectorFetchResult(error=ConnectorError("C-ATTACHMENT-CONVERT-FAILED", str(exc)))

        links = payload.get("_links") if isinstance(payload.get("_links"), dict) else {}
        webui = links.get("webui") or ""
        base = links.get("base") or _load_settings().CONFLUENCE_BASE_URL.rstrip("/")
        url = f"{base}{webui}" if webui else ""
        container = payload.get("container") if isinstance(payload.get("container"), dict) else {}

        return ConnectorFetchResult(
            item=SourceItem(
                source_type=self.source_type,
                external_ref=descriptor.external_ref,
                title=filename,
                markdown=converted.markdown,
                url=url,
                labels=list(converted.labels),
                metadata={
                    "attachmentId": attachment_id,
                    "containerId": container.get("id"),
                    "containerType": container.get("type"),
                    "mediaType": (payload.get("metadata") or {}).get("mediaType") if isinstance(payload.get("metadata"), dict) else None,
                },
            )
        )
