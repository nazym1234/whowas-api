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


def test_akinator_http_flow() -> None:
    with TestClient(app) as client:
        started = client.post("/akinator/start")
        session_id = started.json()["session_id"]
        answered = client.post(
            "/akinator/answer",
            json={"session_id": session_id, "answer": "yes"},
        )
    assert started.status_code == 200
    assert started.json()["question"]
    assert answered.status_code == 200
    assert answered.json()["progress"] == 2


def test_akinator_rejects_unknown_session() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/akinator/answer",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "answer": "no",
            },
        )
    assert response.status_code == 404
