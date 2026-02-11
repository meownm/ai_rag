import importlib
import json
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[4]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    module = importlib.import_module("tools.drift_check")
    return importlib.reload(module)


def test_drift_check_passes_for_current_repo(capsys):
    drift = _load_module()
    assert drift.main() == 0
    out = capsys.readouterr().out
    assert "DRIFT REPORT" in out
    report = json.loads("\n".join(out.splitlines()[1:]))
    assert report["overall_ok"] is True


def test_drift_check_fails_when_report_has_drift(monkeypatch):
    drift = _load_module()
    monkeypatch.setattr(drift, "build_report", lambda: {"overall_ok": False, "sections": [{"name": "endpoints", "missing_in_code": ["/v1/x"], "extra_in_code": [], "ok": False}]})
    assert drift.main() == 1


def test_drift_check_normalizes_allowed_endpoint_and_env_extras(monkeypatch):
    drift = _load_module()

    monkeypatch.setattr(
        drift,
        "build_report",
        lambda: {
            "overall_ok": False,
            "sections": [
                {
                    "name": "endpoints",
                    "missing_in_code": [],
                    "extra_in_code": ["/v1/healthz", "/v1/unexpected"],
                    "ok": False,
                },
                {
                    "name": "env_vars",
                    "missing_in_code": [],
                    "extra_in_code": ["USE_LLM_GENERATION", "USE_CONVERSATION_MEMORY", "UNEXPECTED_FLAG"],
                    "ok": False,
                },
            ],
        },
    )

    assert drift.main() == 1
    normalized = drift._normalize_report(drift.build_report())
    endpoint_section = next(s for s in normalized["sections"] if s["name"] == "endpoints")
    env_section = next(s for s in normalized["sections"] if s["name"] == "env_vars")
    assert endpoint_section["extra_in_code"] == ["/v1/unexpected"]
    assert env_section["extra_in_code"] == ["UNEXPECTED_FLAG"]


def test_drift_check_epic08_env_flags_are_allowlisted():
    drift = _load_module()
    epic08_flags = {
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

    assert epic08_flags.issubset(drift._ALLOWED_ENV_EXTRAS)


def test_drift_check_keeps_non_allowlisted_epic08_like_env(monkeypatch):
    drift = _load_module()

    monkeypatch.setattr(
        drift,
        "build_report",
        lambda: {
            "overall_ok": False,
            "sections": [
                {
                    "name": "env_vars",
                    "missing_in_code": [],
                    "extra_in_code": ["USE_CONVERSATION_MEMORY", "REWRITE_UNKNOWN_FLAG"],
                    "ok": False,
                }
            ],
        },
    )

    normalized = drift._normalize_report(drift.build_report())
    env_section = next(s for s in normalized["sections"] if s["name"] == "env_vars")
    assert env_section["extra_in_code"] == ["REWRITE_UNKNOWN_FLAG"]
    assert normalized["overall_ok"] is False
