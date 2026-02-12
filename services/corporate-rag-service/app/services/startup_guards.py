from __future__ import annotations

from app.clients.ollama_client import OllamaClient
from app.core.config import settings
from app.core.logging import log_event


class StartupValidationError(RuntimeError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def validate_model_context_windows() -> None:
    if not settings.VERIFY_MODEL_NUM_CTX:
        log_event("startup.context.verification.skipped", payload={"verify_model_num_ctx": False}, plane="control")
        return

    model_id = settings.LLM_MODEL
    configured_window = int(settings.LLM_NUM_CTX)
    provider = OllamaClient(settings.LLM_ENDPOINT, model_id, settings.REQUEST_TIMEOUT_SECONDS)

    log_event(
        "startup.context.verification.started",
        payload={"model_id": model_id, "configured_num_ctx": configured_window},
        plane="control",
    )

    provider_window = provider.fetch_model_num_ctx(model_id)
    if provider_window is None:
        log_event("startup.provider.num_ctx.unavailable", payload={"model_id": settings.LLM_MODEL}, plane="control")
        return

    provider_int = int(provider_window)
    if provider_int <= 0:
        raise StartupValidationError("CFG-LIMIT-INVALID", f"Provider returned non-positive context limit: {provider_int}")

    if provider_int < configured_window:
        raise StartupValidationError(
            "CFG-LIMIT-OVERFLOW",
            f"Configured num_ctx={configured_window} exceeds provider limit={provider_int} for model={model_id}",
        )

    if provider_int != configured_window:
        if provider_int > configured_window:
            log_event("startup.provider.context.limit.unknown", payload={"model_id": model_id}, plane="control")
    return None
