from __future__ import annotations

from fastapi.testclient import TestClient

from cited_rag.main import create_app


def test_health_returns_200() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_phase_00_contract() -> None:
    client = TestClient(create_app())
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "not_configured"}


def test_correlation_id_is_echoed() -> None:
    client = TestClient(create_app())
    response = client.get("/health", headers={"X-Correlation-ID": "req-test-1"})
    assert response.headers["X-Correlation-ID"] == "req-test-1"
