from pydantic import computed_field, field_validator, model_validator
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
    USE_VECTOR_RETRIEVAL: bool = True
    HYBRID_SCORE_NORMALIZATION: bool = False
    USE_CONTEXTUAL_EXPANSION: bool = False
    NEIGHBOR_WINDOW: int = 1
    CONTEXT_EXPANSION_ENABLED: bool = False
    CONTEXT_EXPANSION_MODE: str = "doc_neighbor"
    CONTEXT_EXPANSION_NEIGHBOR_WINDOW: int = 1
    CONTEXT_EXPANSION_MAX_DOCS: int = 4
    CONTEXT_EXPANSION_MAX_EXTRA_CHUNKS: int = 12
    CONTEXT_EXPANSION_MAX_LINK_DOCS: int = 1
    CONTEXT_EXPANSION_REDUNDANCY_SIM_THRESHOLD: float = 0.92
    CONTEXT_EXPANSION_MIN_GAIN: float = 0.01
    CONTEXT_EXPANSION_TOPK_BASE: int = 8
    CONTEXT_EXPANSION_TOPK_HARD_CAP: int = 20
    USE_TOKEN_BUDGET_ASSEMBLY: bool = True
    MAX_CONTEXT_TOKENS: int = 65536
    MODEL_CONTEXT_WINDOW: int = 65536
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


    CONNECTOR_REGISTRY_ENABLED: bool = True
    CONNECTOR_SYNC_MAX_ITEMS_PER_RUN: int = 5000
    CONNECTOR_SYNC_PAGE_SIZE: int = 100
    CONNECTOR_INCREMENTAL_ENABLED: bool = True

    CONFLUENCE_BASE_URL: str = ""
    CONFLUENCE_AUTH_MODE: str = "pat"
    CONFLUENCE_PAT: str = ""
    CONFLUENCE_USERNAME: str = ""
    CONFLUENCE_PASSWORD: str = ""
    CONFLUENCE_SPACE_KEYS: str = ""
    CONFLUENCE_CQL: str = ""
    CONFLUENCE_FETCH_BODY_REPRESENTATION: str = "storage"
    CONFLUENCE_REQUEST_TIMEOUT_SECONDS: int = 30
    CONFLUENCE_RATE_LIMIT_RPS: float = 3.0

    FILE_CATALOG_ROOT_PATH: str = ""
    FILE_CATALOG_RECURSIVE: bool = True
    FILE_CATALOG_ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt,.md"
    FILE_CATALOG_MAX_FILE_MB: int = 50

    S3_CATALOG_BUCKET: str = ""
    S3_CATALOG_PREFIX: str = ""
    S3_CATALOG_ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt,.md"
    S3_CATALOG_MAX_OBJECT_MB: int = 50

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
    LLM_NUM_CTX: int = 65536
    OLLAMA_KEEP_ALIVE_SECONDS: int = 20

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


    @field_validator("LLM_NUM_CTX")
    @classmethod
    def validate_llm_num_ctx(cls, value: int) -> int:
        allowed = {65536, 131072, 262144}
        if value not in allowed:
            raise ValueError(f"LLM_NUM_CTX must be one of {sorted(allowed)}")
        return value

    @model_validator(mode="after")
    def validate_context_window_consistency(self) -> "Settings":
        if self.MODEL_CONTEXT_WINDOW != self.LLM_NUM_CTX:
            raise ValueError("MODEL_CONTEXT_WINDOW must be equal to LLM_NUM_CTX")
        if self.MAX_CONTEXT_TOKENS > self.LLM_NUM_CTX:
            raise ValueError("MAX_CONTEXT_TOKENS must be less than or equal to LLM_NUM_CTX")
        return self

    @computed_field
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()
