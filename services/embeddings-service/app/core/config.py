from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "embeddings-service"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    EMBEDDINGS_SERVICE_PORT: int = 8200
    OLLAMA_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 1024
    EMBEDDINGS_DEFAULT_MODEL_ID: str = "bge-m3"

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
    EMBEDDINGS_SERVICE_URL: str = "http://localhost:8200"
    RAG_SERVICE_PORT: int = 8100
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")


settings = Settings()
