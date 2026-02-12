from app.services.connectors.confluence import storage_html_to_markdown
from app.services.ingestion import chunk_markdown


def test_chm_sp7_structured_content_regression_integration():
    xhtml = """
    <h1>Architecture</h1>
    <p>Overview section.</p>
    <ul><li>Top item<ul><li>Nested item</li></ul></li></ul>
    <table>
      <tr><th>Key</th><th>Value</th></tr>
      <tr><td rowspan='2'>Timeout</td><td>30</td></tr>
      <tr><td>60</td></tr>
    </table>
    <ac:structured-macro ac:name="code">
      <ac:parameter ac:name="language">python</ac:parameter>
      <ac:plain-text-body><![CDATA[def run():
    return 1]]></ac:plain-text-body>
    </ac:structured-macro>
    <ac:structured-macro ac:name="info"><ac:rich-text-body><p>Important note</p></ac:rich-text-body></ac:structured-macro>
    """

    markdown = storage_html_to_markdown(xhtml)
    chunks = chunk_markdown(markdown)
    assert chunks

    assert "# Architecture" in markdown
    chunk_texts = "\n".join(c["chunk_text"] for c in chunks)
    assert "Timeout" in chunk_texts
    assert "Nested item" in chunk_texts
    assert "def run()" in chunk_texts
    assert "Important note" in chunk_texts

    # pseudo-citation style check: chunk path metadata present for retrieval contexts
    assert any(c.get("chunk_path") for c in chunks)
