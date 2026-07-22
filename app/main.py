import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from types import FunctionType
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.config import setup_logging
from app.core.logging import bind_context, clear_context, get_logger

load_dotenv()

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage application startup and shutdown events."""
    logger.info("Application startup complete", version="0.1.0")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(title="NRPilot API", lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(
    request: Request, call_next: FunctionType
) -> Any | JSONResponse:
    """Middleware to log HTTP requests and responses with structured logging."""
    clear_context()
    request_id: str = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    bind_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query=dict(request.query_params),
    )

    logger.info("Request started")

    try:
        response = await call_next(request)
        logger.info(
            "Request completed",
            status_code=response.status_code,
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        logger.exception(
            "Request failed",
            error=str(exc),
        )
        return JSONResponse(
            {"detail": "Internal server error", "request_id": request_id},
            status_code=500,
        )
    finally:
        clear_context()


app.include_router(health_router)
app.include_router(chat_router)
