from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from cited_rag.adapters.persistence.postgres.uow import PostgresUnitOfWork
from cited_rag.api.deps import get_principal, get_uow
from cited_rag.application.upload import create_collection, owned_collection_or_none
from cited_rag.domain.models.principal import ApiPrincipal

router = APIRouter()


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class CollectionResponse(BaseModel):
    collection_id: UUID
    name: str
    status: str


@router.get("/v1/collections")
async def list_collections(
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
) -> list[CollectionResponse]:
    collections = await uow.collections.list_by_owner(principal.id)
    return [
        CollectionResponse(
            collection_id=collection.id, name=collection.name, status=collection.status.value
        )
        for collection in collections
    ]


@router.post("/v1/collections", status_code=status.HTTP_201_CREATED)
async def post_collection(
    body: CreateCollectionRequest,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
) -> CollectionResponse:
    collection = await create_collection(uow, name=body.name, owner_id=principal.id)
    return CollectionResponse(
        collection_id=collection.id, name=collection.name, status=collection.status.value
    )


@router.get("/v1/collections/{collection_id}")
async def get_collection(
    collection_id: UUID,
    principal: ApiPrincipal = Depends(get_principal),
    uow: PostgresUnitOfWork = Depends(get_uow),
) -> CollectionResponse:
    collection = owned_collection_or_none(await uow.collections.get(collection_id), principal.id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection_not_found")
    return CollectionResponse(
        collection_id=collection.id, name=collection.name, status=collection.status.value
    )
