from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_uses_supported_setting_names_only():
    env_text = (SERVICE_ROOT / ".env.example").read_text(encoding="utf-8")
    lines = {line.strip() for line in env_text.splitlines() if line.strip() and not line.startswith("#")}
    assert all(not line.startswith("PORT=") for line in lines)
    assert all(not line.startswith("S3_ENDPOINT_URL=") for line in lines)
    assert all(not line.startswith("S3_BUCKET=") for line in lines)
    assert any(line.startswith("SERVICE_PORT=") for line in lines)
    assert "MODEL_CONTEXT_WINDOW=" in env_text
    assert "LLM_NUM_CTX=" in env_text


def test_only_canonical_embeddings_client_exists():
    assert (SERVICE_ROOT / "app/clients/embeddings_client.py").exists()
    assert not (SERVICE_ROOT / "app/services/embeddings_client.py").exists()


def test_query_pipeline_does_not_use_getenv():
    code = (SERVICE_ROOT / "app/services/query_pipeline.py").read_text(encoding="utf-8")
    assert "getenv(" not in code
