import importlib
import sys
from pathlib import Path


def _load_detector_module():
    scripts_dir = Path(__file__).resolve().parents[4] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    module = importlib.import_module("drift_detector")
    return importlib.reload(module)


def test_drift_detector_report_structure_positive():
    detector = _load_detector_module()
    report = detector.build_report()
    assert "overall_ok" in report
    assert "sections" in report
    assert isinstance(report["sections"], list)


def test_drift_detector_has_env_section():
    detector = _load_detector_module()
    report = detector.build_report()
    names = {section["name"] for section in report["sections"]}
    assert "env_vars" in names
    assert "job_status:model" in names
