"""Add bloqueada to VacanteEstado

Revision ID: a59f38fd6cba
Revises: aa815f7d24f3
Create Date: 2026-09-13 00:50:45.158182

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a59f38fd6cba'
down_revision: str | None = 'aa815f7d24f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use execute with connection because ALTER TYPE cannot run inside a transaction block easily
    # but Alembic might wrap it in a transaction. We can just execute the alter type statement.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE vacante_estado ADD VALUE IF NOT EXISTS 'bloqueada'")


def downgrade() -> None:
    # PostgreSQL doesn't support dropping enum values easily, so we leave it as is or change rows.
    pass

