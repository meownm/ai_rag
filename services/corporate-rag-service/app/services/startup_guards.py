from __future__ import annotations

import logging

from app.clients.ollama_client import OllamaClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class StartupValidationError(RuntimeError):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


def validate_model_context_windows(client: OllamaClient | None = None) -> None:
    if not settings.VERIFY_MODEL_NUM_CTX:
        logger.info("startup_context_verification_skipped", extra={"verify_model_num_ctx": False})
        return

    ollama_client = client or OllamaClient(settings.LLM_ENDPOINT, settings.LLM_MODEL, settings.REQUEST_TIMEOUT_SECONDS)

    if settings.MODEL_CONTEXT_WINDOW <= 0:
        raise StartupValidationError("MODEL_CONTEXT_MISMATCH", "MODEL_CONTEXT_WINDOW must be positive")

    actual_num_ctx = ollama_client.fetch_model_num_ctx(settings.LLM_MODEL)
    logger.info(
        "startup_model_context_window_check",
        extra={
            "model_id": settings.LLM_MODEL,
            "actual_num_ctx": actual_num_ctx,
            "configured_model_context_window": settings.MODEL_CONTEXT_WINDOW,
        },
    )
    if actual_num_ctx is None:
        logger.warning("provider_num_ctx_unavailable", extra={"model_id": settings.LLM_MODEL})
    elif settings.MODEL_CONTEXT_WINDOW > actual_num_ctx:
        raise StartupValidationError(
            "MODEL_CONTEXT_MISMATCH",
            f"MODEL_CONTEXT_WINDOW={settings.MODEL_CONTEXT_WINDOW} exceeds model num_ctx={actual_num_ctx}",
        )

    # SP7: provider compatibility check for each configured generation model.
    for model_id in {settings.LLM_MODEL, settings.REWRITE_MODEL_ID}:
        provider_limit = ollama_client.fetch_model_num_ctx(model_id)
        if provider_limit is None:
            logger.warning("provider_context_limit_unknown", extra={"model_id": model_id})
            continue
        if settings.MODEL_CONTEXT_WINDOW > provider_limit:
            raise StartupValidationError(
                "MODEL_CONTEXT_MISMATCH",
                f"MODEL_CONTEXT_WINDOW={settings.MODEL_CONTEXT_WINDOW} exceeds provider_limit={provider_limit} for model {model_id}",
            )
