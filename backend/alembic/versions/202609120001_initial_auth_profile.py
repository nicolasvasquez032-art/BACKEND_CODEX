"""initial auth and candidate profile

Revision ID: 202609120001
Revises:
Create Date: 2026-09-12 00:01:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202609120001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    user_role = postgresql.ENUM("CANDIDATE", "COMPANY", "ADMIN", name="user_role")

    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)

    op.create_table(
        "perfiles_candidato",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String(length=80)), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=180), nullable=True),
        sa.Column("education", sa.String(length=180), nullable=True),
        sa.Column("cv_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_perfiles_candidato_user_id"),
        "perfiles_candidato",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_perfiles_candidato_user_id"), table_name="perfiles_candidato")
    op.drop_table("perfiles_candidato")
    op.drop_index(op.f("ix_usuarios_email"), table_name="usuarios")
    op.drop_table("usuarios")
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)

