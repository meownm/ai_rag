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
