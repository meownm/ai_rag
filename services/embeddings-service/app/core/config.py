import logging
import os

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEPRECATED_UNUSED_KEYS = (
    "RERANKER_MODEL",
    "RERANKER_TOP_K",
    "DEFAULT_TOP_K",
    "REQUEST_TIMEOUT_SECONDS",
    "EMBEDDINGS_TIMEOUT_SECONDS",
    "MAX_EMBED_BATCH_SIZE",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DATABASE_URL",
    "PGVECTOR_ENABLED",
    "S3_ENDPOINT",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_BUCKET_RAW",
    "S3_BUCKET_MARKDOWN",
    "S3_REGION",
    "S3_SECURE",
    "EMBEDDINGS_SERVICE_URL",
)


class Settings(BaseSettings):
    APP_NAME: str = "embeddings-service"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    SERVICE_PORT: int = Field(
        default=8200,
        validation_alias=AliasChoices("SERVICE_PORT", "EMBEDDINGS_SERVICE_PORT", "RAG_SERVICE_PORT", "PORT"),
    )

    EMBEDDING_DIM: int = 1024
    EMBEDDINGS_DEFAULT_MODEL_ID: str = "bge-m3"

    LLM_PROVIDER: str = "ollama"
    LLM_ENDPOINT: str = Field(
        default="http://localhost:11434/api/generate",
        validation_alias=AliasChoices("LLM_ENDPOINT", "OLLAMA_BASE_URL"),
    )
    LLM_MODEL: str = Field(
        default="BAAI/bge-small-en-v1.5",
        validation_alias=AliasChoices("LLM_MODEL", "OLLAMA_MODEL", "DEFAULT_MODEL_ID"),
    )
    LLM_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        allowed = {"ollama", "openai", "other"}
        normalized = value.lower().strip()
        if normalized not in allowed:
            raise ValueError(f"LLM_PROVIDER must be one of {sorted(allowed)}")
        return normalized

    @model_validator(mode="after")
    def validate_numeric_ranges(self) -> "Settings":
        if self.SERVICE_PORT < 1 or self.SERVICE_PORT > 65535:
            raise ValueError("SERVICE_PORT must be between 1 and 65535")
        if self.EMBEDDING_DIM < 1:
            raise ValueError("EMBEDDING_DIM must be >= 1")
        return self

    @model_validator(mode="after")
    def validate_deprecated_aliases(self) -> "Settings":
        logger = logging.getLogger(__name__)

        if os.getenv("EMBEDDINGS_SERVICE_PORT"):
            logger.warning("EMBEDDINGS_SERVICE_PORT is deprecated; use SERVICE_PORT")
        if os.getenv("RAG_SERVICE_PORT"):
            logger.warning("RAG_SERVICE_PORT is deprecated; use SERVICE_PORT")
        if os.getenv("PORT"):
            logger.warning("PORT is deprecated; use SERVICE_PORT")

        if os.getenv("OLLAMA_MODEL") or os.getenv("DEFAULT_MODEL_ID"):
            logger.warning("OLLAMA_MODEL and DEFAULT_MODEL_ID are deprecated; use LLM_MODEL")
        if os.getenv("OLLAMA_BASE_URL"):
            logger.warning("OLLAMA_BASE_URL is deprecated; use LLM_ENDPOINT")

        for key in _DEPRECATED_UNUSED_KEYS:
            if os.getenv(key):
                logger.warning("%s is deprecated and ignored", key)

        if os.getenv("SERVICE_PORT") and os.getenv("EMBEDDINGS_SERVICE_PORT"):
            if os.getenv("SERVICE_PORT") != os.getenv("EMBEDDINGS_SERVICE_PORT"):
                raise ValueError("SERVICE_PORT and EMBEDDINGS_SERVICE_PORT are both set with different values")
        if os.getenv("SERVICE_PORT") and os.getenv("PORT"):
            if os.getenv("SERVICE_PORT") != os.getenv("PORT"):
                raise ValueError("SERVICE_PORT and PORT are both set with different values")

        if os.getenv("LLM_MODEL") and os.getenv("OLLAMA_MODEL"):
            if os.getenv("LLM_MODEL") != os.getenv("OLLAMA_MODEL"):
                raise ValueError("LLM_MODEL and OLLAMA_MODEL are both set with different values")
        if os.getenv("LLM_ENDPOINT") and os.getenv("OLLAMA_BASE_URL"):
            normalized_ollama = f"{os.getenv('OLLAMA_BASE_URL', '').rstrip('/')}/api/generate"
            if os.getenv("LLM_ENDPOINT") not in {os.getenv("OLLAMA_BASE_URL"), normalized_ollama}:
                raise ValueError("LLM_ENDPOINT and OLLAMA_BASE_URL are both set with different values")

        if os.getenv("OLLAMA_BASE_URL") and not os.getenv("LLM_ENDPOINT"):
            endpoint = self.LLM_ENDPOINT.rstrip("/")
            if not endpoint.endswith("/api/generate"):
                self.LLM_ENDPOINT = f"{endpoint}/api/generate"

        return self


settings = Settings()
