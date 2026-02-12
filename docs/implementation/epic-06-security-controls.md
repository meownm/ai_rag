# EPIC-6 — Security hardening stop-points

Owner: Security  
Reviewed by: Architect

## SEC-1 — Prompt injection mitigation

Implemented protections in `POST /v1/query` request flow:

- Detection of malicious instructions in user query.
- Stripping directives that attempt external tool execution (shell/browser/package install/file exfiltration hints).
- Preventing system prompt override attempts by stripping lines that request override/reveal behavior.
- Logging sanitized security events via `ERROR` log records with code `SECURITY_PROMPT_SANITIZED`.

## SEC-2 — Rate limiting

Added in-memory per-user limiter with two controls:

- Per-user request limit over a sliding window.
- Burst control (max requests per second per user).

Behavior:

- User identity is read from `X-User-Id` header (falls back to `anonymous`).
- Exceeded limits return `429` with `RATE_LIMIT_EXCEEDED`.

## SEC-3 — RBAC for debug

Added debug-mode role gating (trace logs emitted only when debug is explicitly enabled by admin):

- Debug request is read from `X-Debug-Mode` (`true/1/yes/on`).
- User role is read from `X-User-Role`.
- Only role matching `DEBUG_ADMIN_ROLE` (default `admin`) can enable debug.
- Non-admin debug attempts return `403` with `DEBUG_FORBIDDEN`.

## Test coverage

Added/updated automated tests:

- Unit tests for prompt sanitization + rate limiter (`tests/unit/test_security.py`).
- Integration tests for all EPIC-6 controls (`tests/integration/test_security_controls_integration.py`).

Coverage includes both positive and negative scenarios.
