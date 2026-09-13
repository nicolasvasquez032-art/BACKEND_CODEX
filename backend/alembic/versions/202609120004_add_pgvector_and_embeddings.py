"""Add pgvector and embeddings.

Revision ID: 202609120004
Revises: 202609120003
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "202609120004"
down_revision: str | None = "202609120003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. Habilitar la extensión vector en PostgreSQL
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Agregar la columna embedding a perfiles_candidato
    op.add_column(
        "perfiles_candidato",
        sa.Column("embedding", Vector(384), nullable=True)
    )

    # 3. Agregar la columna embedding a vacantes
    op.add_column(
        "vacantes",
        sa.Column("embedding", Vector(384), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("vacantes", "embedding")
    op.drop_column("perfiles_candidato", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector;")
