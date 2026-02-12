from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSecurityResult:
    sanitized_query: str
    malicious_instruction_detected: bool
    stripped_external_tool_directives: bool
    stripped_system_override_attempt: bool


_SYSTEM_OVERRIDE_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"(reveal|show|print)\s+(the\s+)?system\s+prompt",
    r"(you\s+are\s+now|act\s+as)\s+(a\s+)?system",
    r"override\s+(safety|policy|guardrails?)",
)

_EXTERNAL_TOOL_PATTERNS = (
    r"\b(use|run|execute|call)\b.{0,40}\b(shell|terminal|bash|powershell|python|tool|browser|curl|wget)\b",
    r"\b(install|pip\s+install|apt\s+install|brew\s+install)\b",
    r"\b(read|open|print)\b.{0,40}\b(/etc/passwd|\.env|secret|token|key)\b",
)


def sanitize_user_query(query: str) -> PromptSecurityResult:
    text = (query or "").strip()
    if not text:
        return PromptSecurityResult("", False, False, False)

    stripped_external = False
    stripped_override = False
    clean_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in _EXTERNAL_TOOL_PATTERNS):
            stripped_external = True
            continue

        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in _SYSTEM_OVERRIDE_PATTERNS):
            stripped_override = True
            continue

        clean_lines.append(raw_line)

    sanitized = "\n".join(clean_lines).strip()
    malicious_detected = stripped_external or stripped_override
    if not sanitized:
        sanitized = "[sanitized user request]"

    return PromptSecurityResult(
        sanitized_query=sanitized,
        malicious_instruction_detected=malicious_detected,
        stripped_external_tool_directives=stripped_external,
        stripped_system_override_attempt=stripped_override,
    )


class InMemoryRateLimiter:
    def __init__(self, window_seconds: int, per_user_limit: int, burst_limit: int, max_users: int = 10000):
        self.window_seconds = max(1, int(window_seconds))
        self.per_user_limit = max(1, int(per_user_limit))
        self.burst_limit = max(1, int(burst_limit))
        self.max_users = max(1, int(max_users))
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, events: deque[float], now: float) -> None:
        threshold = now - self.window_seconds
        while events and events[0] <= threshold:
            events.popleft()

    def _can_register_burst(self, events: deque[float], now: float) -> bool:
        burst_threshold = now - 1.0
        recent = 0
        for ts in reversed(events):
            if ts <= burst_threshold:
                break
            recent += 1
            if recent >= self.burst_limit:
                return False
        return True

    def allow(self, user_id: str) -> bool:
        key = (user_id or "anonymous").strip() or "anonymous"
        now = time.monotonic()
        events = self._events[key]
        self._prune(events, now)

        if len(events) >= self.per_user_limit:
            return False

        if not self._can_register_burst(events, now):
            return False

        events.append(now)
        if len(self._events) > self.max_users:
            # best-effort bounded cleanup in insertion order across map keys
            for cleanup_key in list(self._events.keys())[: len(self._events) - self.max_users]:
                self._events.pop(cleanup_key, None)
        return True

    def reset(self) -> None:
        self._events.clear()
