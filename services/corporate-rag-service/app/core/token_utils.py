"""Unified token estimation utilities."""

from __future__ import annotations

TRUNCATION_MARKER = "\n[TRUNCATED_BY_TOKEN_BUDGET]"


def _tiktoken_estimate(text: str) -> int:
    import tiktoken  # type: ignore

    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken with word-based fallback."""
    if not text or not text.strip():
        return 0
    try:
        return _tiktoken_estimate(text)
    except Exception:  # noqa: BLE001
        words = word_count(text)
        return max(1, round(words * 1.33))


def word_count(text: str) -> int:
    """Count non-empty whitespace-separated tokens."""
    return len([t for t in text.split() if t])


def truncate_text_to_tokens(text: str, budget_tokens: int) -> str:
    """Truncate *text* so it fits within *budget_tokens* (approximate)."""
    if budget_tokens <= 0:
        return TRUNCATION_MARKER

    words = text.split()
    if not words:
        return TRUNCATION_MARKER

    approx_words_budget = max(1, int(budget_tokens / 1.33))
    truncated = " ".join(words[:approx_words_budget])
    return f"{truncated}{TRUNCATION_MARKER}"
