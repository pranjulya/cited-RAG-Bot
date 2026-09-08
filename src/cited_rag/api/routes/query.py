from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.api.deps import get_principal, get_settings_dep, get_uow
from cited_rag.application.query import answer_question
from cited_rag.application.upload import owned_collection_or_none
from cited_rag.config import Settings
from cited_rag.domain.exceptions import (
    CitationValidationError,
    DenseRetrievalError,
    GenerationError,
    HybridFusionError,
    RerankerError,
    SparseRetrievalError,
)
from cited_rag.domain.models.chunk import Chunk
from cited_rag.domain.models.principal import ApiPrincipal

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class CitationBody(BaseModel):
    document_id: UUID
    document_version_id: UUID
    document_name: str
    page_start: int
    page_end: int


class QueryResponse(BaseModel):
    request_id: UUID
    status: str
    answer: str
    citations: list[CitationBody]
    reason: str | None = None


def _http_for_query_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CitationValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="citation_validation_failed",
        )
    if isinstance(
        exc,
        (
            DenseRetrievalError,
            SparseRetrievalError,
            HybridFusionError,
            RerankerError,
            GenerationError,
        ),
    ):
        detail = getattr(exc, "failure_code", "query_failed").lower()
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="query_failed")


@router.post("/v1/collections/{collection_id}/query")
async def post_query(
    collection_id: UUID,
    body: QueryRequest,
    request: Request,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
    settings: Settings = Depends(get_settings_dep),
) -> QueryResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_question")
    collection = owned_collection_or_none(await uow.collections.get(collection_id), principal.id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection_not_found")
    store = getattr(request.app.state, "retrieval_store", None)
    embedder = getattr(request.app.state, "embedder", None)
    encoder = getattr(request.app.state, "sparse_encoder", None)
    reranker = getattr(request.app.state, "reranker", None)
    generator = getattr(request.app.state, "generator", None)
    missing = store is None or embedder is None or encoder is None
    if missing or reranker is None or generator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="query_dependencies_unavailable",
        )
    assert store is not None
    assert embedder is not None
    assert encoder is not None
    assert reranker is not None
    assert generator is not None
    version_ids = await uow.documents.list_searchable_version_ids(collection_id)
    chunks: list[Chunk] = []
    names: dict[UUID, str] = {}
    for version_id in version_ids:
        chunks.extend(await uow.chunks.list_by_version(version_id))
        version = await uow.versions.get(version_id)
        if version is not None:
            names[version.document_id] = version.original_filename
    try:
        outcome = await answer_question(
            question,
            collection_id=collection_id,
            document_version_ids=version_ids,
            chunks=chunks,
            document_names=names,
            embedder=embedder,
            encoder=encoder,
            store=store,
            reranker=reranker,
            generator=generator,
            settings=settings,
        )
    except Exception as exc:
        raise _http_for_query_error(exc) from exc
    return QueryResponse(
        request_id=outcome.request_id,
        status=outcome.status.value,
        answer=outcome.answer,
        citations=[
            CitationBody(
                document_id=item.document_id,
                document_version_id=item.document_version_id,
                document_name=item.document_name,
                page_start=item.page_start,
                page_end=item.page_end,
            )
            for item in outcome.citations
        ],
        reason=outcome.reason.value if outcome.reason is not None else None,
    )
