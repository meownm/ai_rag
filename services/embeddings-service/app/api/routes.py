import logging
import time

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.schemas.api import EmbeddingData, EmbeddingsRequest, EmbeddingsResponse, EmbeddingsUsage, ErrorResponse, HealthResponse
from app.services.encoder import EmbeddingDimensionMismatchError, EncoderRegistry

router = APIRouter()
LOGGER = logging.getLogger(__name__)


registry = EncoderRegistry(expected_dim=settings.EMBEDDING_DIM)


@router.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=settings.APP_VERSION)


@router.get("/v1/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(
        version=settings.APP_VERSION,
        default_model_id=settings.EMBEDDINGS_DEFAULT_MODEL_ID,
        embedding_dim=settings.EMBEDDING_DIM,
        loaded_models=registry.loaded_models(),
    )


@router.post("/v1/embeddings", response_model=EmbeddingsResponse, responses={422: {"model": ErrorResponse}})
def create_embeddings(payload: EmbeddingsRequest, request: Request) -> EmbeddingsResponse:
    start = time.perf_counter()
    model_id = payload.model or settings.EMBEDDINGS_DEFAULT_MODEL_ID
    encoder = registry.get_encoder(model_id)
    vectors = encoder.encode(payload.input)

    try:
        embedding_dim = registry.validate_embedding_dim(model_id, vectors)
    except EmbeddingDimensionMismatchError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": str(exc),
                "error_code": "E-EMB-DIM-MISMATCH",
            },
        ) from exc

    duration_ms = int((time.perf_counter() - start) * 1000)
    LOGGER.info(
        "embeddings_generated",
        extra={
            "request_id": request.headers.get("x-request-id"),
            "model_id": model_id,
            "embedding_dim": embedding_dim,
            "batch_size": len(payload.input),
            "duration_ms": duration_ms,
        },
    )
    return EmbeddingsResponse(
        model=model_id,
        data=[EmbeddingData(index=i, embedding=e) for i, e in enumerate(vectors)],
        usage=EmbeddingsUsage(input_texts=len(payload.input), total_tokens_estimate=sum(len(x.split()) for x in payload.input)),
    )
