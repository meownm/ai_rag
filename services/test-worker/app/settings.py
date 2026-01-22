from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "test-worker"
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 54210

    log_level: str = "INFO"
    log_format: str = "json"
    log_data_mode: str = "plain"

    mq_host: str = "localhost"
    mq_port: int = 54040
    mq_user: str = "rag_mq"
    mq_password: str = "rag_mq_pass"
    mq_vhost: str = "/"

    health_path: str = "/health"
    ready_path: str = "/ready"
    metrics_path: str = "/metrics"

    worker_queue_name: str = "kb.worker.test-worker"
    worker_prefetch: int = 50
    worker_concurrency: int = 8
    worker_handler_timeout_seconds: int = 10

    worker_max_attempts: int = 3
    worker_dlq_suffix: str = ".dlq"
    worker_retry_suffix: str = ".retry"
    worker_retry_delay_ms: int = 2000


def load_settings() -> Settings:
    return Settings()
