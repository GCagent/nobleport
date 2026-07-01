"""Operational health endpoints with explicit deployment evidence."""

from __future__ import annotations

from typing import Dict, Tuple

from fastapi import APIRouter, Request, Response, status

from .settings import get_settings

router = APIRouter(tags=["health"])


async def database_status() -> Tuple[bool, str]:
    """Perform a minimal database reachability check without logging credentials."""
    settings = get_settings()
    if not settings.DATABASE_URL:
        return False, "not_configured"

    try:
        import asyncpg

        connection = await asyncpg.connect(settings.DATABASE_URL, timeout=3)
        try:
            await connection.execute("SELECT 1")
        finally:
            await connection.close()
    except Exception:  # Health output must not leak driver/connection details.
        return False, "unreachable"
    return True, "connected"


@router.get("/health/live")
async def live() -> Dict[str, str]:
    """Process liveness only; suitable for container restarts."""
    settings = get_settings()
    return {
        "status": "alive",
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
    }


@router.get("/health/ready")
async def ready(request: Request, response: Response) -> Dict[str, object]:
    """Readiness stays false until verified dependencies and operating gates are met."""
    settings = get_settings()
    database_ok, database_state = await database_status()
    config_errors = list(getattr(request.app.state, "config_errors", settings.validation_errors()))
    persistence = getattr(
        request.app.state,
        "gcagent_persistence",
        {"ok": False, "backend": "unknown", "state": "not_initialized"},
    )
    legacy_status = {
        "ok": settings.is_production,
        "state": "disabled_in_production" if settings.is_production else "staged_simulation_only",
    }

    checks = {
        "configuration": {"ok": not config_errors, "errors": config_errors},
        "database": {"ok": database_ok, "state": database_state},
        "field_ops_persistence": persistence,
        "legacy_investor_workflow": legacy_status,
    }
    ready_state = all(check["ok"] for check in checks.values())
    if not ready_state:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready_state else "not_ready",
        "environment": settings.APP_ENV,
        "checks": checks,
    }
