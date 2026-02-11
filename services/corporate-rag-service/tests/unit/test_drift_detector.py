import importlib
import sys
from pathlib import Path


def _write_pyproject(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


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


def test_extract_poetry_runtime_dependencies_positive(tmp_path):
    detector = _load_detector_module()
    pyproject = tmp_path / "pyproject.toml"
    _write_pyproject(
        pyproject,
        """
[tool.poetry]
name = "sample"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
""".strip(),
    )

    deps = detector._extract_poetry_runtime_dependencies(pyproject)
    assert deps == {"fastapi": "^0.115.0", "uvicorn": "^0.30.0"}


def test_extract_poetry_runtime_dependencies_negative_ignores_unversioned(tmp_path):
    detector = _load_detector_module()
    pyproject = tmp_path / "pyproject.toml"
    _write_pyproject(
        pyproject,
        """
[tool.poetry]
name = "sample"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = {extras = ["all"]}
""".strip(),
    )

    deps = detector._extract_poetry_runtime_dependencies(pyproject)
    assert deps == {}


def test_build_shared_runtime_dependency_section_negative_mismatch(monkeypatch):
    detector = _load_detector_module()

    def _fake_extract(path: Path) -> dict[str, str]:
        if str(path).endswith("corporate-rag-service/pyproject.toml"):
            return {"fastapi": "^0.115.0", "uvicorn": "^0.30.0"}
        return {"fastapi": "^0.114.0", "uvicorn": "^0.30.0"}

    monkeypatch.setattr(detector, "_extract_poetry_runtime_dependencies", _fake_extract)
    section = detector._build_shared_runtime_dependency_section()
    assert section["ok"] is False
    assert section["mismatches"] == ["fastapi:rag=^0.115.0,embeddings=^0.114.0"]
