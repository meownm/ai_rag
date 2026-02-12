from datetime import datetime, timezone

from app.services.connectors.base import SyncContext
from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown


class FakeConfluenceClient:
    def __init__(self):
        self.list_calls: list[dict] = []
        self.fetch_calls: list[dict] = []

    def list_pages(self, *, cql: str, start: int, limit: int):
        self.list_calls.append({"cql": cql, "start": start, "limit": limit})
        if start == 0:
            return [
                {
                    "id": "101",
                    "title": "Page A",
                    "space": {"key": "ENG"},
                    "version": {"number": 3, "when": "2024-01-02T10:20:30Z"},
                }
            ]
        return []

    def fetch_page_body_by_id(self, page_id: str, *, representation: str):
        self.fetch_calls.append({"page_id": page_id, "representation": representation})
        return {
            "id": page_id,
            "title": "Page A",
            "version": {"number": 3, "when": "2024-01-02T10:20:30Z"},
            "body": {
                representation: {
                    "value": "<h1>Title</h1><p>hello world</p><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
                }
            },
            "_links": {"base": "https://conf.local", "webui": "/spaces/ENG/pages/101"},
        }


def test_chm_sp1_macro_and_namespace_preprocess_positive():
    xhtml = """
    <ac:structured-macro ac:name="info"><ac:rich-text-body><p>Read this</p></ac:rich-text-body></ac:structured-macro>
    <ac:structured-macro ac:name="code"><ac:parameter ac:name="language">python</ac:parameter><ac:plain-text-body><![CDATA[print('ok')]]></ac:plain-text-body></ac:structured-macro>
    <ac:link><ri:attachment ri:filename="report.pdf"/></ac:link>
    <script>alert(1)</script>
    """
    md = storage_html_to_markdown(xhtml)
    assert "ac:" not in md
    assert "> **INFO:** Read this" in md
    assert "```python" in md
    assert "print('ok')" in md
    assert "(attachment:report.pdf)" in md
    assert "alert(1)" not in md


def test_chm_sp2_table_normalization_rowspan_colspan_positive():
    md = storage_html_to_markdown(
        "<table><tr><th>A</th><th>B</th><th>C</th></tr>"
        "<tr><td rowspan='2'>1</td><td colspan='2'>2</td></tr>"
        "<tr><td>3</td><td>4</td></tr></table>"
    )
    assert "| A | B | C |" in md
    assert "| 1 | 2 | 2 |" in md
    assert "| 1 | 3 | 4 |" in md


def test_chm_sp2_header_only_table_positive():
    md = storage_html_to_markdown("<table><tr><th>Only</th><th>Headers</th></tr></table>")
    assert "| Only | Headers |" in md
    assert "| --- | --- |" in md


def test_chm_sp3_nested_lists_three_levels_positive():
    md = storage_html_to_markdown(
        "<ol><li>One<ul><li>Sub A<ul><li>Sub A.1</li></ul></li></ul></li><li>Two</li></ol>"
    )
    assert "1. One" in md
    assert "  - Sub A" in md
    assert "    - Sub A.1" in md
    assert "2. Two" in md


def test_chm_sp5_pre_code_language_preserved_positive():
    md = storage_html_to_markdown('<pre><code class="language-sql">select\n  1;</code></pre>')
    assert "```sql" in md
    assert "select\n  1;" in md


def test_chm_sp6_determinism_hash_equal_positive():
    sample = "<h2>Head</h2><p>A</p><table><tr><th>X</th></tr><tr><td>Y</td></tr></table>"
    first = storage_html_to_markdown(sample)
    second = storage_html_to_markdown(sample)
    assert first == second


def test_confluence_pages_connector_two_step_pagination_positive(monkeypatch):
    from app.services.connectors import confluence as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_CQL", "")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_SPACE_KEYS", "ENG")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_FETCH_BODY_REPRESENTATION", "storage")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    fake_client = FakeConfluenceClient()
    connector = ConfluencePagesConnector(client=fake_client)

    descriptors = connector.list_descriptors(
        tenant_id="t1",
        sync_context=SyncContext(max_items_per_run=10, page_size=1, incremental_enabled=True),
    )
    assert len(descriptors) == 1
    assert descriptors[0].external_ref == "page:101"
    assert descriptors[0].checksum_hint == "v:3"
    assert descriptors[0].last_modified == datetime(2024, 1, 2, 10, 20, 30, tzinfo=timezone.utc)

    result = connector.fetch_item("t1", descriptors[0])
    assert result.error is None
    assert result.item is not None
    assert "| A | B |" in result.item.markdown
    assert "hello world" in result.item.markdown
    assert result.item.metadata["spaceKey"] == "ENG"

    assert len(fake_client.list_calls) >= 1
    assert len(fake_client.fetch_calls) == 1


class FakeConfluenceAttachmentClient(FakeConfluenceClient):
    def __init__(self):
        super().__init__()
        self.download_calls: list[str] = []

    def list_attachments(self, *, cql: str, start: int, limit: int):
        self.list_calls.append({"cql": cql, "start": start, "limit": limit})
        if start == 0:
            return [
                {
                    "id": "att-1",
                    "title": "policy.md",
                    "container": {"id": "101", "type": "page"},
                    "version": {"number": 5, "when": "2024-01-02T10:20:30Z"},
                    "metadata": {"mediaType": "text/markdown"},
                }
            ]
        return []

    def fetch_attachment_by_id(self, attachment_id: str):
        self.fetch_calls.append({"attachment_id": attachment_id})
        return {
            "id": attachment_id,
            "title": "policy.md",
            "container": {"id": "101", "type": "page"},
            "metadata": {"mediaType": "text/markdown"},
            "_links": {"base": "https://conf.local", "webui": "/download/attachments/101/policy.md", "download": "/download/attachments/101/policy.md"},
        }

    def download_attachment(self, download_url: str) -> bytes:
        self.download_calls.append(download_url)
        return b"# Policy\n\nAll hands"


def test_confluence_attachment_connector_positive(monkeypatch):
    from app.services.connectors import confluence as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_CQL", "")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_SPACE_KEYS", "ENG")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    client = FakeConfluenceAttachmentClient()
    connector = module.ConfluenceAttachmentConnector(client=client)

    descriptors = connector.list_descriptors(
        tenant_id="t1",
        sync_context=SyncContext(max_items_per_run=10, page_size=1, incremental_enabled=True),
    )

    assert len(descriptors) == 1
    assert descriptors[0].external_ref == "attachment:att-1"

    result = connector.fetch_item("t1", descriptors[0])
    assert result.error is None
    assert result.item is not None
    assert result.item.source_type == "CONFLUENCE_ATTACHMENT"
    assert "# Policy" in result.item.markdown
    assert result.item.metadata["containerId"] == "101"
    assert len(client.download_calls) == 1


def test_confluence_attachment_connector_negative_unsupported_extension(monkeypatch):
    from app.services.connectors import confluence as module

    class UnsupportedAttachmentClient(FakeConfluenceAttachmentClient):
        def fetch_attachment_by_id(self, attachment_id: str):
            payload = super().fetch_attachment_by_id(attachment_id)
            payload["title"] = "archive.zip"
            payload["metadata"] = {"mediaType": "application/octet-stream"}
            return payload

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = module.ConfluenceAttachmentConnector(client=UnsupportedAttachmentClient())
    descriptor = module.SourceDescriptor(
        source_type="CONFLUENCE_ATTACHMENT",
        external_ref="attachment:att-1",
        title="archive.zip",
        metadata={"attachment_id": "att-1"},
    )

    result = connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "C-ATTACHMENT-UNSUPPORTED-TYPE"



def test_confluence_attachment_connector_negative_missing_download(monkeypatch):
    from app.services.connectors import confluence as module

    class NoDownloadClient(FakeConfluenceAttachmentClient):
        def fetch_attachment_by_id(self, attachment_id: str):
            payload = super().fetch_attachment_by_id(attachment_id)
            payload["_links"].pop("download", None)
            return payload

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = module.ConfluenceAttachmentConnector(client=NoDownloadClient())
    descriptor = module.SourceDescriptor(
        source_type="CONFLUENCE_ATTACHMENT",
        external_ref="attachment:att-1",
        title="policy.md",
        metadata={"attachment_id": "att-1"},
    )

    result = connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "C-ATTACHMENT-MISSING-DOWNLOAD"


def test_confluence_attachment_connector_positive_media_type_fallback(monkeypatch):
    from app.services.connectors import confluence as module

    class NoExtensionClient(FakeConfluenceAttachmentClient):
        def fetch_attachment_by_id(self, attachment_id: str):
            payload = super().fetch_attachment_by_id(attachment_id)
            payload["title"] = "policy"
            payload["metadata"] = {"mediaType": "text/markdown"}
            return payload

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = module.ConfluenceAttachmentConnector(client=NoExtensionClient())
    descriptor = module.SourceDescriptor(
        source_type="CONFLUENCE_ATTACHMENT",
        external_ref="attachment:att-1",
        title="policy",
        metadata={"attachment_id": "att-1"},
    )

    result = connector.fetch_item("t1", descriptor)
    assert result.error is None
    assert result.item is not None
    assert result.item.title.endswith(".md")


def test_confluence_attachment_connector_negative_fetch_failed(monkeypatch):
    import httpx
    from app.services.connectors import confluence as module

    class BrokenClient(FakeConfluenceAttachmentClient):
        def fetch_attachment_by_id(self, attachment_id: str):
            raise httpx.HTTPError("boom")

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    connector = module.ConfluenceAttachmentConnector(client=BrokenClient())
    descriptor = module.SourceDescriptor(
        source_type="CONFLUENCE_ATTACHMENT",
        external_ref="attachment:att-1",
        title="policy.md",
        metadata={"attachment_id": "att-1"},
    )

    result = connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "C-ATTACHMENT-FETCH-FAILED"
    assert result.error.retryable is True


def test_confluence_pages_connector_negative_empty_body(monkeypatch):
    class EmptyBodyClient(FakeConfluenceClient):
        def fetch_page_body_by_id(self, page_id: str, *, representation: str):
            return {"title": "X", "body": {representation: {"value": ""}}}

    from app.services.connectors import confluence as module

    fake_settings = module._load_settings()
    monkeypatch.setattr(fake_settings, "CONFLUENCE_BASE_URL", "https://conf.local")
    monkeypatch.setattr(fake_settings, "CONFLUENCE_PAT", "token")
    monkeypatch.setattr(module, "_load_settings", lambda: fake_settings)

    descriptor_client = FakeConfluenceClient()
    connector = ConfluencePagesConnector(client=descriptor_client)
    descriptor = connector.list_descriptors("t1", SyncContext(max_items_per_run=1, page_size=1, incremental_enabled=True))[0]

    empty_connector = ConfluencePagesConnector(client=EmptyBodyClient())
    result = empty_connector.fetch_item("t1", descriptor)
    assert result.item is None
    assert result.error is not None
    assert result.error.error_code == "C-EMPTY-BODY"
