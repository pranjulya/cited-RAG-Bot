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


def test_cors_allows_origin_on_health() -> None:
    from cited_rag.config import Settings
    from cited_rag.main import create_app as _create_app

    settings = Settings(_env_file=None, environment="test", cors_allow_origins="*")
    client = TestClient(_create_app(settings))
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
