from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "corporate-rag-service"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8100
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rag"
    embeddings_service_url: str = "http://localhost:8200"
    reranker_model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    min_sentence_similarity: float = 0.65
    min_lexical_overlap: float = 0.25
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "rag-documents"
    rerank_top_n: int = 20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
