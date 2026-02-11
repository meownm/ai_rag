import importlib
import sys
from pathlib import Path


def _load_detector_module():
    scripts_dir = Path(__file__).resolve().parents[4] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module = importlib.import_module("drift_detector")
    return importlib.reload(module)


def test_drift_report_contains_dependency_runtime_section():
    detector = _load_detector_module()
    report = detector.build_report()
    section = next(item for item in report["sections"] if item["name"] == "dependencies:shared_python_runtime")
    assert section["ok"] is True
    assert "fastapi" in section["checked"]
