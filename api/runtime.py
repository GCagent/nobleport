"""HTTP middleware and FastAPI lifespan helpers."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .settings import get_settings

logger = logging.getLogger("nobleport.runtime")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds a correlation id, conservative security headers, and timing output."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Server-Timing"] = f"app;dur={duration_ms}"

        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        logger.info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def configure_runtime(app: FastAPI) -> None:
    """Install host and request controls before routes are served."""
    settings = get_settings()
    app.add_middleware(RequestContextMiddleware)
    if settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


@asynccontextmanager
async def application_lifespan(app: FastAPI):
    """Validate settings and manage the field-operations repository lifecycle."""
    settings = get_settings()
    app.state.started_at = time.time()
    app.state.config_errors = settings.validation_errors()

    if settings.is_production:
        settings.validate_runtime()

    from .gcagent import configure_repository, shutdown_repository

    try:
        app.state.gcagent_persistence = await configure_repository()
    except Exception as exc:
        app.state.gcagent_persistence = {
            "ok": False,
            "backend": settings.PERSISTENCE_BACKEND,
            "state": "repository_initialization_failed",
        }
        app.state.config_errors.append("GCagent repository initialization failed")
        logger.exception("gcagent_repository_initialization_failed")
        if settings.is_production:
            raise RuntimeError("GCagent persistent repository initialization failed") from exc

    try:
        yield
    finally:
        await shutdown_repository()
