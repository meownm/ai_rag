"""Token estimation utilities used by chunking.

The default estimator remains ``split`` for backwards-compatible runtime behavior.
Set ``TOKEN_ESTIMATOR=tiktoken`` to use tiktoken when installed.
"""


def split_token_count(text: str) -> int:
    return len([t for t in text.split() if t])


def tiktoken_token_count(text: str) -> int:
    try:
        import tiktoken
    except Exception:  # noqa: BLE001
        return split_token_count(text)

    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def token_count(text: str, *, estimator: str = "split") -> int:
    if estimator == "tiktoken":
        return tiktoken_token_count(text)
    return split_token_count(text)
