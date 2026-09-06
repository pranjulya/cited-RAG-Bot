"""Composite provenance foreign keys.

Revision ID: 0002_provenance_constraints
Revises: 0001_core_metadata
Create Date: 2026-09-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_provenance_constraints"
down_revision: str | None = "0001_core_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_documents_id_collection", "documents", ["id", "collection_id"])
    op.create_unique_constraint(
        "uq_document_versions_id_document", "document_versions", ["id", "document_id"]
    )
    op.create_unique_constraint(
        "uq_document_versions_id_document_collection",
        "document_versions",
        ["id", "document_id", "collection_id"],
    )
    op.create_foreign_key(
        "fk_document_versions_document_collection",
        "document_versions",
        "documents",
        ["document_id", "collection_id"],
        ["id", "collection_id"],
    )
    op.drop_constraint("fk_documents_active_version", "documents", type_="foreignkey")
    op.create_foreign_key(
        "fk_documents_active_version_same_document",
        "documents",
        "document_versions",
        ["id", "active_version_id"],
        ["document_id", "id"],
    )
    op.create_foreign_key(
        "fk_chunks_version_document_collection",
        "chunks",
        "document_versions",
        ["document_version_id", "document_id", "collection_id"],
        ["id", "document_id", "collection_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_chunks_version_document_collection", "chunks", type_="foreignkey")
    op.drop_constraint("fk_documents_active_version_same_document", "documents", type_="foreignkey")
    op.create_foreign_key(
        "fk_documents_active_version",
        "documents",
        "document_versions",
        ["active_version_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_document_versions_document_collection", "document_versions", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_document_versions_id_document_collection", "document_versions", type_="unique"
    )
    op.drop_constraint("uq_document_versions_id_document", "document_versions", type_="unique")
    op.drop_constraint("uq_documents_id_collection", "documents", type_="unique")
