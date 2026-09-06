from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cited_rag.config import Settings
from cited_rag.main import create_app


def test_factory_app_serves_health_without_external_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CITED_RAG_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None, environment="test", api_key="test-placeholder-key")
    with TestClient(create_app(settings)) as client:
        health = client.get("/health")
        ready = client.get("/ready")
    assert health.status_code == 200
    assert ready.status_code == 503
    assert ready.json()["detail"]["reason"] == "database"
