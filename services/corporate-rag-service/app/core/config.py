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
    EMBEDDINGS_DEFAULT_MODEL_ID: str = "bge-m3"
    EMBEDDINGS_BATCH_SIZE: int = 64
    EMBEDDINGS_RETRY_ATTEMPTS: int = 3
    USE_VECTOR_RETRIEVAL: bool = False
    HYBRID_SCORE_NORMALIZATION: bool = False
    USE_CONTEXTUAL_EXPANSION: bool = False
    NEIGHBOR_WINDOW: int = 1
    USE_TOKEN_BUDGET_ASSEMBLY: bool = False
    MAX_CONTEXT_TOKENS: int = 8000
    MODEL_CONTEXT_WINDOW: int = 8000
    VERIFY_MODEL_NUM_CTX: bool = True
    USE_LLM_GENERATION: bool = False

    USE_CONVERSATION_MEMORY: bool = False
    USE_LLM_QUERY_REWRITE: bool = False
    USE_CLARIFICATION_LOOP: bool = False
    CONVERSATION_TURNS_LAST_N: int = 8
    CONVERSATION_SUMMARY_THRESHOLD_TURNS: int = 12
    CONVERSATION_TTL_MINUTES: int = 30
    REWRITE_CONFIDENCE_THRESHOLD: float = 0.55
    REWRITE_MODEL_ID: str = "qwen3:14b-instruct"
    REWRITE_KEEP_ALIVE: int = 0
    REWRITE_MAX_CONTEXT_TOKENS: int = 2048
    MAX_CLARIFICATION_DEPTH: int = 2
    CONFIDENCE_FALLBACK_THRESHOLD: float = 0.3
    ENABLE_PER_STAGE_LATENCY_METRICS: bool = True

    CHUNK_TARGET_TOKENS: int = 650
    CHUNK_MAX_TOKENS: int = 900
    CHUNK_MIN_TOKENS: int = 120
    CHUNK_OVERLAP_TOKENS: int = 80

    LOG_DATA_MODE: str = "PLAIN"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 20

    LLM_PROVIDER: str = "ollama"
    LLM_ENDPOINT: str = "http://localhost:11434/api/generate"
    LLM_MODEL: str = "qwen3:14b-instruct"
    LLM_API_KEY: str = ""

    REQUEST_TIMEOUT_SECONDS: int = 30
    EMBEDDINGS_TIMEOUT_SECONDS: int = 30
    MAX_EMBED_BATCH_SIZE: int = 64
    DEFAULT_TOP_K: int = 5

    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PER_USER: int = 30
    RATE_LIMIT_BURST: int = 10
    RATE_LIMIT_STORAGE_MAX_USERS: int = 10000

    DEBUG_ADMIN_ROLE: str = "admin"

    MIN_SENTENCE_SIMILARITY: float = 0.65
    MIN_LEXICAL_OVERLAP: float = 0.25

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")

    @computed_field
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()
