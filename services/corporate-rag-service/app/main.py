import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.logging import clear_request_context, configure_logging, log_event, set_request_context
from app.services.startup_guards import StartupValidationError, validate_model_context_windows

configure_logging()
app = FastAPI(title="Corporate RAG Service API", version=settings.APP_VERSION)
app.include_router(router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    tenant_id = request.headers.get("X-Tenant-ID")
    set_request_context(request_id=request_id, tenant_id=tenant_id)
    request.state.request_id = request_id
    request.state.tenant_id = tenant_id

    req_size = int(request.headers.get("content-length") or 0)
    status_code = 500
    response_size = 0
    error_code = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        response_size = int(response.headers.get("content-length") or 0)
        if status_code >= 400:
            error_code = str(status_code)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        error_code = "internal_server_error"
        raise
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        log_event(
            "api.request.completed",
            payload={
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "request_size_bytes": req_size,
                "response_size_bytes": response_size,
                "error_code": error_code,
            },
            plane="data",
        )
        clear_request_context()


@app.exception_handler(HTTPException)
async def contract_error_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return await http_exception_handler(request, exc)


@app.on_event("startup")
def _startup_validation() -> None:
    if settings.PGVECTOR_ENABLED and not settings.USE_VECTOR_RETRIEVAL:
        log_event("startup_vector_retrieval_disabled_with_pgvector", payload={"pgvector_enabled": settings.PGVECTOR_ENABLED, "use_vector_retrieval": settings.USE_VECTOR_RETRIEVAL}, plane="control")
    try:
        validate_model_context_windows()
        log_event("startup.completed", payload={"message": "startup validation passed"}, plane="control")
    except StartupValidationError as exc:
        log_event("startup.failed", level=40, payload={"error_code": exc.error_code}, plane="control")
        raise RuntimeError(f"{exc.error_code}: {exc}") from exc
