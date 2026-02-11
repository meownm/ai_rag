import logging
import time
from functools import lru_cache

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.api import EmbeddingData, EmbeddingsRequest, EmbeddingsResponse, EmbeddingsUsage, HealthResponse
from app.services.encoder import EncoderService

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@lru_cache
def get_encoder() -> EncoderService:
    return EncoderService(settings.OLLAMA_MODEL)


@router.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=settings.APP_VERSION)


@router.post("/v1/embeddings", response_model=EmbeddingsResponse)
def create_embeddings(payload: EmbeddingsRequest) -> EmbeddingsResponse:
    start = time.perf_counter()
    vectors = get_encoder().encode(payload.input)
    duration_ms = int((time.perf_counter() - start) * 1000)
    LOGGER.info("embeddings_generated", extra={"model": payload.model, "batch_size": len(payload.input), "duration_ms": duration_ms})
    return EmbeddingsResponse(
        model=payload.model,
        data=[EmbeddingData(index=i, embedding=e) for i, e in enumerate(vectors)],
        usage=EmbeddingsUsage(input_texts=len(payload.input), total_tokens_estimate=sum(len(x.split()) for x in payload.input)),
    )
