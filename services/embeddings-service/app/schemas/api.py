from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "embeddings-service"
    version: str
    default_model_id: str | None = None
    embedding_dim: int | None = None
    loaded_models: list[str] = Field(default_factory=list)


class EmbeddingsRequest(BaseModel):
    model: str | None = None
    input: list[str] = Field(min_length=1, max_length=256)
    encoding_format: str = "float"
    tenant_id: UUID | None = None
    correlation_id: UUID | None = None


class EmbeddingData(BaseModel):
    index: int
    embedding: list[float]


class EmbeddingsUsage(BaseModel):
    input_texts: int
    total_tokens_estimate: int


class EmbeddingsResponse(BaseModel):
    object: str = "list"
    model: str
    data: list[EmbeddingData]
    usage: EmbeddingsUsage


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
