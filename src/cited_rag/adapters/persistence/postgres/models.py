from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from cited_rag.adapters.persistence.postgres.base import Base
from cited_rag.domain.enums import (
    CollectionStatus,
    DocumentVersionStatus,
    IngestionJobStatus,
    QueryRunStatus,
)


def _in_enum(column: str, values: list[str]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class ApiPrincipalRow(Base):
    __tablename__ = "api_principals"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CollectionRow(Base):
    __tablename__ = "collections"
    __table_args__ = (
        CheckConstraint(
            _in_enum("status", [status.value for status in CollectionStatus]),
            name="ck_collections_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("api_principals.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentRow(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("id", "collection_id", name="uq_documents_id_collection"),
        ForeignKeyConstraint(
            ["id", "active_version_id"],
            ["document_versions.document_id", "document_versions.id"],
            name="fk_documents_active_version_same_document",
            use_alter=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    collection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("collections.id"), nullable=False
    )
    logical_name: Mapped[str] = mapped_column(String(512), nullable=False)
    active_version_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentVersionRow(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_number"),
        UniqueConstraint("id", "document_id", name="uq_document_versions_id_document"),
        UniqueConstraint(
            "id",
            "document_id",
            "collection_id",
            name="uq_document_versions_id_document_collection",
        ),
        ForeignKeyConstraint(
            ["document_id", "collection_id"],
            ["documents.id", "documents.collection_id"],
            name="fk_document_versions_document_collection",
        ),
        CheckConstraint(
            _in_enum("ingestion_status", [status.value for status in DocumentVersionStatus]),
            name="ck_document_versions_status",
        ),
        Index(
            "uq_document_versions_collection_content_hash_active",
            "collection_id",
            "content_hash",
            unique=True,
            postgresql_where=text("ingestion_status <> 'DELETED'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    collection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("collections.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PageRow(Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("document_version_id", "page_number", name="uq_pages_version_number"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class ChunkRow(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_version_id", "chunk_order", name="uq_chunks_version_order"),
        Index("ix_chunks_collection_id", "collection_id"),
        ForeignKeyConstraint(
            ["document_version_id", "document_id", "collection_id"],
            [
                "document_versions.id",
                "document_versions.document_id",
                "document_versions.collection_id",
            ],
            name="fk_chunks_version_document_collection",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    collection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("collections.id"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False
    )
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IngestionJobRow(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        UniqueConstraint("document_version_id", name="uq_ingestion_jobs_version"),
        CheckConstraint(
            _in_enum("status", [status.value for status in IngestionJobStatus]),
            name="ck_ingestion_jobs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QueryRunRow(Base):
    __tablename__ = "query_runs"
    __table_args__ = (
        CheckConstraint(
            _in_enum("status", [status.value for status in QueryRunStatus]),
            name="ck_query_runs_status",
        ),
        Index("ix_query_runs_collection_id", "collection_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    collection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("collections.id"), nullable=False
    )
    principal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("api_principals.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
