from __future__ import annotations


class DatabaseOperationError(RuntimeError):
    def __init__(self, *, error_code: str, sqlstate: str | None, retryable: bool) -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.sqlstate = sqlstate
        self.retryable = retryable
