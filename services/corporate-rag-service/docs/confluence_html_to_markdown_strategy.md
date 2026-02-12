# Confluence storage XHTML -> Markdown strategy

## Goals

- Deterministic conversion for identical input snapshots.
- Preserve structural semantics for headings, nested lists, tables, and code.
- Safely sanitize unsupported/unsafe macros and tags.

## Conversion pipeline

1. Preprocess and sanitize storage XHTML:
   - remove `<script>` / `<style>` blocks;
   - parse with namespace-aware XML wrapper for `ac:` and `ri:`;
   - normalize whitespace to deterministic single-space runs.
2. Macro handling:
   - `ac:structured-macro[name=code]` -> fenced code block with language;
   - `info` / `note` -> markdown blockquote with uppercase label;
   - `expand` -> synthetic heading + body text;
   - unsupported macros -> deterministic placeholder `[macro:<name>]`.
3. Table normalization:
   - expand `rowspan`/`colspan` to rectangular grid;
   - preserve header row when `<th>` exists;
   - emit GitHub-flavored markdown table.
4. List conversion:
   - preserve nested `<ul>/<ol>` depth with indentation;
   - preserve ordered-list numbering sequence.
5. Code blocks:
   - preserve multiline formatting in triple-backtick fences;
   - capture language from macro parameter or `language-*` class.

## Ingestion impact

- Visible markdown structure is preserved.
- Existing chunking behavior remains unchanged.
- `chunk_path` (heading path) continues to be part of embedding input.
