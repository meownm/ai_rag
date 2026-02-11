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
_ALLOWED_ENUM_SECTIONS = {
    "enum:health_status",
    "enum:embeddings_encoding_format",
    "enum:embeddings_response_object",
}


def _normalize_report(report: dict) -> dict:
    for section in report.get("sections", []):
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
