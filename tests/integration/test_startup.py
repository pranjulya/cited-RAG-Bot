from __future__ import annotations

from fastapi.testclient import TestClient

from cited_rag.main import create_app


def test_factory_app_serves_health_without_external_dependencies() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/health")
        ready = client.get("/ready")
    assert health.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["status"] == "not_configured"
