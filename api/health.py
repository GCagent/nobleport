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
    """Readiness is intentionally false until persistence and runtime gates are proven."""
    settings = get_settings()
    database_ok, database_state = await database_status()
    config_errors = list(getattr(request.app.state, "config_errors", settings.validation_errors()))

    checks = {
        "configuration": {"ok": not config_errors, "errors": config_errors},
        "database": {"ok": database_ok, "state": database_state},
        "field_ops_persistence": {
            "ok": not settings.uses_in_memory_persistence,
            "state": settings.PERSISTENCE_BACKEND,
        },
        "legacy_investor_workflow": {
            "ok": False,
            "state": "staged_simulation_only",
        },
    }
    ready_state = all(check["ok"] for check in checks.values())
    if not ready_state:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready_state else "not_ready",
        "environment": settings.APP_ENV,
        "checks": checks,
    }
