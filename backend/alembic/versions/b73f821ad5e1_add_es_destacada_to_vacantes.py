"""add es_destacada to vacantes

Revision ID: b73f821ad5e1
Revises: e2a255a7eed6
Create Date: 2026-11-16 15:40:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b73f821ad5e1'
down_revision: str | None = '5e65383ca1d9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('vacantes', sa.Column('es_destacada', sa.Boolean(), server_default='false', nullable=False))
    op.create_index(op.f('ix_vacantes_es_destacada'), 'vacantes', ['es_destacada'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_vacantes_es_destacada'), table_name='vacantes')
    op.drop_column('vacantes', 'es_destacada')
