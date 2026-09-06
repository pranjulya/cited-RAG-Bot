from __future__ import annotations

from fastapi.testclient import TestClient

from cited_rag.main import create_app


def test_health_returns_200() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_unavailable_without_database() -> None:
    client = TestClient(create_app())
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "not_ready"


def test_correlation_id_is_echoed() -> None:
    client = TestClient(create_app())
    response = client.get("/health", headers={"X-Correlation-ID": "req-test-1"})
    assert response.headers["X-Correlation-ID"] == "req-test-1"
