from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from cited_rag.api.deps import _bearer_matches, get_principal, get_uow
from cited_rag.api.routes.documents import _document_status_response
from cited_rag.config import Settings
from cited_rag.domain.enums import DocumentVersionStatus
from cited_rag.domain.models.collection import Collection
from cited_rag.domain.models.document import Document, DocumentVersion
from cited_rag.domain.models.principal import ApiPrincipal
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


def test_document_status_includes_failure_fields_when_failed() -> None:
    document = Document(collection_id=uuid4(), logical_name="scan")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=document.collection_id,
        version_number=1,
        content_hash="h",
        original_filename="scan.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://a.pdf",
        ingestion_status=DocumentVersionStatus.FAILED,
        failure_code="PDF_UNSUPPORTED",
        failure_message=(
            "PDF has no extractable text (scanned or image-only pages); pypdf has no OCR"
        ),
    )
    body = _document_status_response(document, version)
    dumped = body.model_dump()
    assert dumped["status"] == "FAILED"
    assert dumped["failure_code"] == "PDF_UNSUPPORTED"
    assert dumped["failure_message"] is not None
    assert "OCR" in dumped["failure_message"]


def test_document_status_omits_failure_fields_when_not_failed() -> None:
    document = Document(collection_id=uuid4(), logical_name="ok")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=document.collection_id,
        version_number=1,
        content_hash="h",
        original_filename="ok.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://a.pdf",
        ingestion_status=DocumentVersionStatus.READY,
        failure_code="PDF_UNSUPPORTED",
        failure_message="should not leak",
    )
    dumped = _document_status_response(document, version).model_dump()
    assert dumped["status"] == "READY"
    assert dumped["failure_code"] is None
    assert dumped["failure_message"] is None


def test_document_get_body_includes_failure_code_when_failed() -> None:
    principal = ApiPrincipal(name="test")
    collection = Collection(name="c", owner_id=principal.id)
    document = Document(collection_id=collection.id, logical_name="scan")
    version = DocumentVersion(
        document_id=document.id,
        collection_id=collection.id,
        version_number=1,
        content_hash="h",
        original_filename="scan.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://a.pdf",
        ingestion_status=DocumentVersionStatus.FAILED,
        failure_code="PDF_UNSUPPORTED",
        failure_message=(
            "PDF has no extractable text (scanned or image-only pages); pypdf has no OCR"
        ),
    )
    app = create_app(Settings(_env_file=None, api_key="test-placeholder-key", environment="test"))

    class _Documents:
        async def get(self, _document_id: object) -> Document:
            return document

    class _Collections:
        async def get(self, _collection_id: object) -> Collection:
            return collection

    class _Versions:
        async def list_by_document(self, _document_id: object) -> list[DocumentVersion]:
            return [version]

    class _Uow:
        documents = _Documents()
        collections = _Collections()
        versions = _Versions()

    async def _uow() -> object:
        yield _Uow()

    async def _principal() -> ApiPrincipal:
        return principal

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_principal] = _principal
    client = TestClient(app)
    response = client.get(
        f"/v1/documents/{document.id}",
        headers={"Authorization": "Bearer test-placeholder-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["failure_code"] == "PDF_UNSUPPORTED"
    assert "OCR" in body["failure_message"]


def test_list_collections_returns_only_the_authenticated_principals_collections() -> None:
    principal = ApiPrincipal(name="owner")
    owned = Collection(name="handbooks", owner_id=principal.id)
    other = Collection(name="private", owner_id=uuid4())
    app = create_app(Settings(_env_file=None, api_key="test-placeholder-key", environment="test"))

    class _Collections:
        async def list_by_owner(self, owner_id: object) -> list[Collection]:
            return [collection for collection in (owned, other) if collection.owner_id == owner_id]

    class _Uow:
        collections = _Collections()

    async def _uow() -> object:
        yield _Uow()

    async def _principal() -> ApiPrincipal:
        return principal

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_principal] = _principal
    client = TestClient(app)

    response = client.get(
        "/v1/collections", headers={"Authorization": "Bearer test-placeholder-key"}
    )

    assert response.status_code == 200
    assert response.json() == [
        {"collection_id": str(owned.id), "name": "handbooks", "status": "ACTIVE"}
    ]


def test_list_documents_returns_current_statuses_for_the_owned_collection() -> None:
    principal = ApiPrincipal(name="owner")
    collection = Collection(name="handbooks", owner_id=principal.id)
    ready = Document(collection_id=collection.id, logical_name="policy.pdf")
    failed = Document(collection_id=collection.id, logical_name="scan.pdf")
    ready_version = DocumentVersion(
        document_id=ready.id,
        collection_id=collection.id,
        version_number=1,
        content_hash="ready",
        original_filename="policy.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://policy.pdf",
        ingestion_status=DocumentVersionStatus.READY,
    )
    failed_version = DocumentVersion(
        document_id=failed.id,
        collection_id=collection.id,
        version_number=1,
        content_hash="failed",
        original_filename="scan.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        storage_uri="local://scan.pdf",
        ingestion_status=DocumentVersionStatus.FAILED,
        failure_code="PDF_UNSUPPORTED",
        failure_message="No extractable text",
    )
    app = create_app(Settings(_env_file=None, api_key="test-placeholder-key", environment="test"))

    class _Collections:
        async def get(self, _collection_id: object) -> Collection:
            return collection

    class _Documents:
        async def list_by_collection(self, _collection_id: object) -> list[Document]:
            return [ready, failed]

    class _Versions:
        async def list_by_document(self, document_id: object) -> list[DocumentVersion]:
            return [ready_version] if document_id == ready.id else [failed_version]

    class _Uow:
        collections = _Collections()
        documents = _Documents()
        versions = _Versions()

    async def _uow() -> object:
        yield _Uow()

    async def _principal() -> ApiPrincipal:
        return principal

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_principal] = _principal
    client = TestClient(app)

    response = client.get(
        f"/v1/collections/{collection.id}/documents",
        headers={"Authorization": "Bearer test-placeholder-key"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "document_id": str(ready.id),
            "collection_id": str(collection.id),
            "logical_name": "policy.pdf",
            "active_version_id": None,
            "document_version_id": str(ready_version.id),
            "version_number": 1,
            "status": "READY",
            "original_filename": "policy.pdf",
            "failure_code": None,
            "failure_message": None,
        },
        {
            "document_id": str(failed.id),
            "collection_id": str(collection.id),
            "logical_name": "scan.pdf",
            "active_version_id": None,
            "document_version_id": str(failed_version.id),
            "version_number": 1,
            "status": "FAILED",
            "original_filename": "scan.pdf",
            "failure_code": "PDF_UNSUPPORTED",
            "failure_message": "No extractable text",
        },
    ]


def test_list_documents_hides_another_principals_collection() -> None:
    principal = ApiPrincipal(name="owner")
    collection = Collection(name="private", owner_id=uuid4())
    app = create_app(Settings(_env_file=None, api_key="test-placeholder-key", environment="test"))

    class _Collections:
        async def get(self, _collection_id: object) -> Collection:
            return collection

    class _Uow:
        collections = _Collections()

    async def _uow() -> object:
        yield _Uow()

    async def _principal() -> ApiPrincipal:
        return principal

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_principal] = _principal
    response = TestClient(app).get(
        f"/v1/collections/{collection.id}/documents",
        headers={"Authorization": "Bearer test-placeholder-key"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "collection_not_found"}
