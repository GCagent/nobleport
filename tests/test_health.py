from fastapi.testclient import TestClient

from api.main import app


def test_liveness_exposes_runtime_identity() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_readiness_is_fail_closed_without_verified_dependencies() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["legacy_investor_workflow"]["state"] == "staged_simulation_only"
