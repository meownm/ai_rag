from app.services.ingestion import chunk_markdown, normalize_to_markdown


def _assert_offsets_consistent(markdown: str) -> None:
    chunks = chunk_markdown(markdown, target_tokens=32, max_tokens=64, min_tokens=1, overlap_tokens=8)
    for chunk in chunks:
        start = int(chunk["char_start"])
        end = int(chunk["char_end"])
        assert markdown[start:end] == chunk["chunk_text"]


def test_offsets_match_chunk_text_on_normalized_markdown():
    raw = "# Header\r\n\r\nText   with   spaces\r\n- item 1\r\n- item 2\r\n"
    normalized = normalize_to_markdown(raw)
    _assert_offsets_consistent(normalized)


def test_offsets_match_on_tables_and_code_blocks():
    markdown = normalize_to_markdown(
        "# T\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```python\nprint('x')\n```\n"
    )
    _assert_offsets_consistent(markdown)
