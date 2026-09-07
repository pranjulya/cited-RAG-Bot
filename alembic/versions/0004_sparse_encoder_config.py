"""Store sparse encoder name/version on document versions.

Revision ID: 0004_sparse_encoder_config
Revises: 0003_chunking_config
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_sparse_encoder_config"
down_revision: str | None = "0003_chunking_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column("sparse_encoder_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_versions", "sparse_encoder_config")
