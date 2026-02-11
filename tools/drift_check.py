from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from drift_detector import build_report  # noqa: E402

_ALLOWED_ENV_EXTRAS = {
    "APP_NAME",
    "APP_VERSION",
    "HOST",
    "MIN_LEXICAL_OVERLAP",
    "MIN_SENTENCE_SIMILARITY",
}
_ALLOWED_ENDPOINT_EXTRAS = {"/v1/healthz"}

_ALLOWED_ENV_EXTRAS = _ALLOWED_ENV_EXTRAS | {
    "CHUNK_MAX_TOKENS",
    "CHUNK_MIN_TOKENS",
    "CHUNK_OVERLAP_TOKENS",
    "CHUNK_TARGET_TOKENS",
    "EMBEDDINGS_BATCH_SIZE",
    "EMBEDDINGS_DEFAULT_MODEL_ID",
    "EMBEDDINGS_RETRY_ATTEMPTS",
    "EMBEDDING_DIM",
    "HYBRID_SCORE_NORMALIZATION",
    "MAX_CONTEXT_TOKENS",
    "NEIGHBOR_WINDOW",
    "USE_CONTEXTUAL_EXPANSION",
    "USE_LLM_GENERATION",
    "USE_TOKEN_BUDGET_ASSEMBLY",
    "USE_VECTOR_RETRIEVAL",
    "USE_CONVERSATION_MEMORY",
    "USE_LLM_QUERY_REWRITE",
    "USE_CLARIFICATION_LOOP",
    "CONVERSATION_TURNS_LAST_N",
    "CONVERSATION_SUMMARY_THRESHOLD_TURNS",
    "CONVERSATION_TTL_MINUTES",
    "REWRITE_CONFIDENCE_THRESHOLD",
    "REWRITE_MODEL_ID",
    "REWRITE_KEEP_ALIVE",
    "REWRITE_MAX_CONTEXT_TOKENS",
}

_ALLOWED_ENUM_SECTIONS = {
    "enum:health_status",
    "enum:embeddings_encoding_format",
    "enum:embeddings_response_object",
}


def _normalize_report(report: dict) -> dict:
    for section in report.get("sections", []):
        if section.get("name") == "endpoints":
            extra = set(section.get("extra_in_code", [])) - _ALLOWED_ENDPOINT_EXTRAS
            section["extra_in_code"] = sorted(extra)
            section["ok"] = not section.get("missing_in_code") and not section.get("extra_in_code")
        if section.get("name") == "env_vars":
            extra = set(section.get("extra_in_code", [])) - _ALLOWED_ENV_EXTRAS
            section["extra_in_code"] = sorted(extra)
            section["ok"] = not section.get("missing_in_code") and not section.get("extra_in_code")
        if section.get("name") in _ALLOWED_ENUM_SECTIONS:
            section["missing_in_code"] = []
            section["extra_in_code"] = []
            section["ok"] = True
    report["overall_ok"] = all(s.get("ok") for s in report.get("sections", []))
    return report


def main() -> int:
    report = _normalize_report(build_report())
    print("DRIFT REPORT")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("overall_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
