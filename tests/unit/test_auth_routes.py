from __future__ import annotations

from fastapi.testclient import TestClient

from cited_rag.api.deps import _bearer_matches
from cited_rag.main import create_app


def test_health_remains_unauthenticated() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503


def test_collection_routes_require_bearer_token() -> None:
    client = TestClient(create_app())
    missing = client.post("/v1/collections", json={"name": "books"})
    assert missing.status_code == 401
    assert missing.headers.get("www-authenticate") == "Bearer"
    wrong = client.post(
        "/v1/collections",
        json={"name": "books"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert wrong.status_code == 401


def test_bearer_compare_accepts_non_ascii_without_raising() -> None:
    assert _bearer_matches("café-key", "test-placeholder-key") is False
    assert _bearer_matches("test-placeholder-key", "test-placeholder-key") is True
