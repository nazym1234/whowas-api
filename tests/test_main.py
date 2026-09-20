from fastapi.testclient import TestClient

from app.main import app


def test_health_and_security_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]


def test_readiness_and_metrics() -> None:
    with TestClient(app) as client:
        readiness = client.get("/health/ready")
        metrics = client.get("/metrics")
    assert readiness.json()["status"] == "ready"
    assert "whowas_requests_total" in metrics.text
