from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "corporate-rag-service"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    RAG_SERVICE_PORT: int = 8100

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "rag"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rag"
    PGVECTOR_ENABLED: bool = True

    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minio"
    S3_SECRET_KEY: str = "minio123"
    S3_BUCKET_RAW: str = "rag-raw"
    S3_BUCKET_MARKDOWN: str = "rag-markdown"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = False

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    EMBEDDINGS_SERVICE_URL: str = "http://localhost:8200"
    EMBEDDINGS_SERVICE_PORT: int = 8200

    LOG_DATA_MODE: str = "PLAIN"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 20

    LLM_PROVIDER: str = "ollama"
    LLM_ENDPOINT: str = "http://localhost:11434/api/generate"
    LLM_MODEL: str = "llama3.1"
    LLM_API_KEY: str = ""

    REQUEST_TIMEOUT_SECONDS: int = 30
    EMBEDDINGS_TIMEOUT_SECONDS: int = 30
    MAX_EMBED_BATCH_SIZE: int = 64
    DEFAULT_TOP_K: int = 5

    MIN_SENTENCE_SIMILARITY: float = 0.65
    MIN_LEXICAL_OVERLAP: float = 0.25

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")

    @computed_field
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()
