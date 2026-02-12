from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.startup_guards import StartupValidationError, validate_model_context_windows

configure_logging()

app = FastAPI(title="Corporate RAG Service API", version=settings.APP_VERSION)
app.include_router(router)


@app.exception_handler(HTTPException)
async def contract_error_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return await http_exception_handler(request, exc)


@app.on_event("startup")
def _startup_validation() -> None:
    try:
        validate_model_context_windows()
    except StartupValidationError as exc:
        raise RuntimeError(f"{exc.error_code}: {exc}") from exc
