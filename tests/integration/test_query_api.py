from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cited_rag.config import Settings
from cited_rag.main import create_app

pytestmark = [pytest.mark.postgres]

AUTH = {"Authorization": "Bearer test-placeholder-key"}


@pytest.fixture
def client(migrated_database: str, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        environment="test",
        api_key="test-placeholder-key",
        database_url=migrated_database,
        local_storage_path=str(tmp_path / "objects"),
        max_upload_bytes=1024 * 1024,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_query_unknown_collection_is_404(client: TestClient) -> None:
    response = client.post(
        f"/v1/collections/{uuid4()}/query",
        json={"question": "How much leave?"},
        headers=AUTH,
    )
    assert response.status_code == 404


def test_query_without_ready_documents_is_insufficient(client: TestClient) -> None:
    created = client.post("/v1/collections", json={"name": "empty"}, headers=AUTH)
    assert created.status_code == 201
    collection_id = created.json()["collection_id"]
    response = client.post(
        f"/v1/collections/{collection_id}/query",
        json={"question": "How much leave?"},
        headers={**AUTH, "X-Correlation-ID": "query-trace-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INSUFFICIENT_EVIDENCE"
    assert body["citations"] == []
    assert body["reason"] == "NO_READY_DOCUMENTS"
    assert response.headers.get("X-Correlation-ID") == "query-trace-1"
    assert "request_id" in body
    assert body["trace"]["correlation_id"] == "query-trace-1"
    assert [stage["name"] for stage in body["trace"]["stages"]] == [
        "query.request",
        "query.fusion",
        "query.rerank",
        "query.context_build",
        "query.generation",
        "query.citation_validate",
    ]
    assert body["trace"]["stages"][0]["status"] == "ok"
    assert all(stage["status"] == "skipped" for stage in body["trace"]["stages"][1:])
    assert body["trace"]["evidence"] == []
