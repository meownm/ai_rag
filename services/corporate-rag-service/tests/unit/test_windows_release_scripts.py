from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[2]


def _read_script(name: str) -> str:
    return (SERVICE_ROOT / name).read_text(encoding="utf-8").lower()


def test_install_script_has_pause_on_error_rule() -> None:
    script = _read_script("install.bat")

    assert "if errorlevel 1 goto :error" in script
    assert ":error" in script
    assert "pause" in script
    assert "exit /b 1" in script


def test_deploy_script_has_pause_on_error_rule() -> None:
    script = _read_script("deploy_docker_desktop.bat")

    assert script.count("if errorlevel 1 goto :error") >= 2
    assert ":error" in script
    assert "pause" in script
    assert "exit /b 1" in script


def test_run_local_script_uses_env_port_and_prints_swagger_url() -> None:
    script = _read_script("run_local.bat")

    assert "title corporate rag service - local run" in script
    assert '"%%~a"=="port"' in script
    assert "swagger url" in script
    assert "pause" in script
    assert script.index("swagger url") < script.index("poetry run uvicorn")


def test_scripts_keep_success_exit_path() -> None:
    install_script = _read_script("install.bat")
    deploy_script = _read_script("deploy_docker_desktop.bat")

    assert "exit /b 0" in install_script
    assert "exit /b 0" in deploy_script
