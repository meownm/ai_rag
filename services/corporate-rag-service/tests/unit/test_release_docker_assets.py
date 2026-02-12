from pathlib import Path


DOCKERFILE_PATH = Path(__file__).resolve().parents[2] / "Dockerfile"


def test_dockerfile_uses_multi_stage_build() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "AS builder" in dockerfile
    assert "AS runtime" in dockerfile
    assert "COPY --from=builder" in dockerfile


def test_dockerfile_uses_clean_runtime_basics() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "rm -rf /var/lib/apt/lists/*" in dockerfile
    assert "USER appuser" in dockerfile
    assert "ENTRYPOINT [\"/app/docker-entrypoint.sh\"]" in dockerfile
