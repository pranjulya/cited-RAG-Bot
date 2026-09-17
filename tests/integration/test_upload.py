from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cited_rag.config import Settings
from cited_rag.main import create_app

pytestmark = pytest.mark.postgres

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
AUTH = {"Authorization": "Bearer test-placeholder-key"}


@pytest.fixture
def client(migrated_database: str, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        environment="test",
        api_key="test-placeholder-key",
        database_url=migrated_database,
        local_storage_path=str(tmp_path / "objects"),
        max_upload_bytes=1024,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _create_collection(client: TestClient, name: str = "handbooks") -> str:
    response = client.post("/v1/collections", json={"name": name}, headers=AUTH)
    assert response.status_code == 201
    return str(response.json()["collection_id"])


def test_create_and_get_collection(client: TestClient) -> None:
    collection_id = _create_collection(client)
    response = client.get(f"/v1/collections/{collection_id}", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["name"] == "handbooks"
    assert response.json()["status"] == "ACTIVE"
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok"}
    blank = client.post("/v1/collections", json={"name": "   "}, headers=AUTH)
    assert blank.status_code == 422


def test_list_collections_starts_empty_and_includes_created_collections(client: TestClient) -> None:
    assert client.get("/v1/collections", headers=AUTH).json() == []
    first_id = _create_collection(client, "handbooks")
    second_id = _create_collection(client, "policies")

    response = client.get("/v1/collections", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == [
        {"collection_id": first_id, "name": "handbooks", "status": "ACTIVE"},
        {"collection_id": second_id, "name": "policies", "status": "ACTIVE"},
    ]


def test_valid_pdf_upload_returns_queued_and_is_not_searchable(client: TestClient) -> None:
    collection_id = _create_collection(client)
    response = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "QUEUED"
    document_id = body["document_id"]
    status = client.get(f"/v1/documents/{document_id}", headers=AUTH)
    assert status.status_code == 200
    assert status.json()["status"] == "QUEUED"
    assert status.json()["active_version_id"] is None


def test_non_pdf_rejected(client: TestClient) -> None:
    collection_id = _create_collection(client)
    response = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.txt", MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_pdf"


def test_empty_file_rejected(client: TestClient) -> None:
    collection_id = _create_collection(client)
    response = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "empty_file"


def test_oversized_file_rejected(client: TestClient) -> None:
    collection_id = _create_collection(client)
    payload = MINIMAL_PDF + b"x" * 2048
    response = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 413


def test_duplicate_content_is_idempotent(client: TestClient) -> None:
    collection_id = _create_collection(client)
    first = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    second = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("copy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["document_id"] == second.json()["document_id"]
    assert first.json()["document_version_id"] == second.json()["document_version_id"]


def test_same_pdf_in_another_collection_is_allowed(client: TestClient) -> None:
    first_id = _create_collection(client, "a")
    second_id = _create_collection(client, "b")
    first = client.post(
        f"/v1/collections/{first_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    second = client.post(
        f"/v1/collections/{second_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert first.json()["document_id"] != second.json()["document_id"]


def test_unknown_document_and_collection_are_404(client: TestClient) -> None:
    missing = uuid4()
    assert client.get(f"/v1/collections/{missing}", headers=AUTH).status_code == 404
    assert client.get(f"/v1/documents/{missing}", headers=AUTH).status_code == 404
    collection_id = _create_collection(client)
    upload = client.post(
        f"/v1/collections/{missing}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 404
    delete = client.delete(f"/v1/documents/{missing}", headers=AUTH)
    assert delete.status_code == 404
    _ = collection_id


def test_delete_document_is_not_gettable(client: TestClient) -> None:
    collection_id = _create_collection(client)
    uploaded = client.post(
        f"/v1/collections/{collection_id}/documents",
        headers=AUTH,
        files={"file": ("policy.pdf", MINIMAL_PDF, "application/pdf")},
    )
    document_id = uploaded.json()["document_id"]
    deleted = client.delete(f"/v1/documents/{document_id}", headers=AUTH)
    assert deleted.status_code == 202
    assert deleted.json()["status"] == "DELETING"
    assert client.get(f"/v1/documents/{document_id}", headers=AUTH).status_code == 404
