import asyncio

import httpx

from api.main import app


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


def test_liveness_exposes_runtime_identity() -> None:
    response = asyncio.run(_get("/health/live"))

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_readiness_is_fail_closed_without_verified_dependencies() -> None:
    response = asyncio.run(_get("/health/ready"))

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["legacy_investor_workflow"]["state"] == "staged_simulation_only"
