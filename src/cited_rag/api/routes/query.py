from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, cast
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
from cited_rag.domain.models.evidence import EvidenceRecord
from cited_rag.domain.models.principal import ApiPrincipal
from cited_rag.domain.models.query_result import QueryOutcome
from cited_rag.observability.stages import QUERY_STAGES
from cited_rag.observability.tracing import Span, start_trace, take_trace

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=20000)


class CitationBody(BaseModel):
    document_id: UUID
    document_version_id: UUID
    document_name: str
    page_start: int
    page_end: int


class TraceStageBody(BaseModel):
    name: str
    duration_ms: int
    status: Literal["ok", "error", "skipped"]


class TraceEvidenceBody(BaseModel):
    id: str
    document_id: UUID
    document_version_id: UUID
    document_name: str
    page_start: int
    page_end: int
    text: str
    truncated: bool


class TraceBody(BaseModel):
    correlation_id: str
    stages: list[TraceStageBody]
    evidence: list[TraceEvidenceBody]


class QueryResponse(BaseModel):
    request_id: UUID
    status: str
    answer: str
    citations: list[CitationBody]
    reason: str | None = None
    trace: TraceBody
    generation_backend: Literal["heuristic", "openai_compatible"]


def _trace_body(
    *,
    spans: Sequence[Span],
    evidence: Sequence[EvidenceRecord],
    correlation_id: str,
    settings: Settings,
) -> TraceBody:
    by_name = {item.name: item for item in spans}
    stages = [
        TraceStageBody(
            name=name,
            duration_ms=by_name[name].duration_ms if name in by_name else 0,
            status=cast(Literal["ok", "error", "skipped"], by_name[name].status)
            if name in by_name
            else "skipped",
        )
        for name in QUERY_STAGES
    ]
    records = []
    for item in evidence[: settings.max_evidence_items]:
        text = item.text[: settings.trace_evidence_chars]
        records.append(
            TraceEvidenceBody(
                id=item.evidence_id,
                document_id=item.document_id,
                document_version_id=item.document_version_id,
                document_name=item.document_name,
                page_start=item.page_start,
                page_end=item.page_end,
                text=text,
                truncated=len(text) < len(item.text),
            )
        )
    return TraceBody(correlation_id=correlation_id, stages=stages, evidence=records)


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
    if len(question) > settings.query_max_chars:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="query_too_long",
        )
    collection = owned_collection_or_none(await uow.collections.get(collection_id), principal.id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection_not_found")
    store = getattr(request.app.state, "retrieval_store", None)
    embedder = getattr(request.app.state, "embedder", None)
    encoder = getattr(request.app.state, "sparse_encoder", None)
    reranker = getattr(request.app.state, "reranker", None)
    generator = getattr(request.app.state, "generator", None)
    decisioner = getattr(request.app.state, "jev_decisioner", None)
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
    start_trace()
    try:
        version_ids = await uow.documents.list_searchable_version_ids(collection_id)
        names: dict[UUID, str] = {}

        async def load_chunks(chunk_ids: Sequence[UUID]) -> list[Chunk]:
            loaded = await uow.chunks.get_many(chunk_ids)
            for chunk in loaded:
                if chunk.document_id in names:
                    continue
                version = await uow.versions.get(chunk.document_version_id)
                if version is not None:
                    names[chunk.document_id] = version.original_filename
            return loaded

        async def _run_query() -> QueryOutcome:
            return await answer_question(
                question,
                collection_id=collection_id,
                document_version_ids=version_ids,
                document_names=names,
                load_chunks=load_chunks,
                embedder=embedder,
                encoder=encoder,
                store=store,
                reranker=reranker,
                generator=generator,
                settings=settings,
                decisioner=decisioner,
                correlation_id=getattr(request.state, "correlation_id", None),
            )

        semaphore = getattr(request.app.state, "query_semaphore", None)
        try:
            if semaphore is None:
                outcome = await _run_query()
            else:
                async with semaphore:
                    outcome = await _run_query()
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
            trace=_trace_body(
                spans=take_trace(),
                evidence=outcome.evidence,
                correlation_id=getattr(request.state, "correlation_id", "-"),
                settings=settings,
            ),
            generation_backend=settings.generation_backend,
        )
    finally:
        take_trace()
