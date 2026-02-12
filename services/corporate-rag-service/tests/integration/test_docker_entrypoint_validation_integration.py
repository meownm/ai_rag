import os
import subprocess
from pathlib import Path


ENTRYPOINT_PATH = Path(__file__).resolve().parents[2] / "docker-entrypoint.sh"


def _run_entrypoint(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env)
    return subprocess.run(
        ["sh", str(ENTRYPOINT_PATH), "sh", "-c", "echo ok"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_entrypoint_accepts_valid_environment() -> None:
    result = _run_entrypoint(
        {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/rag",
            "EMBEDDINGS_SERVICE_URL": "http://embeddings:8200",
        }
    )

    assert result.returncode == 0
    assert "ok" in result.stdout


def test_entrypoint_rejects_invalid_app_env() -> None:
    result = _run_entrypoint(
        {
            "APP_ENV": "qa",
            "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/rag",
            "EMBEDDINGS_SERVICE_URL": "http://embeddings:8200",
        }
    )

    assert result.returncode != 0
    assert "Invalid APP_ENV" in result.stderr


def test_entrypoint_rejects_missing_required_env() -> None:
    result = _run_entrypoint({"APP_ENV": "production", "DATABASE_URL": ""})

    assert result.returncode != 0
    assert "Missing required env var: DATABASE_URL" in result.stderr
