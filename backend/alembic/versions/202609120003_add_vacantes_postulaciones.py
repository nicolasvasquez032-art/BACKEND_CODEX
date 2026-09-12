"""Add vacantes and postulaciones tables.

Revision ID: 202609120003
Revises: 202609120002
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "202609120003"
down_revision: str | None = "202609120002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Enum de estados de vacante
    op.execute("CREATE TYPE vacante_estado AS ENUM ('activa', 'pausada', 'cerrada')")
    # Enum de estados de postulacion
    op.execute(
        "CREATE TYPE postulacion_estado AS ENUM "
        "('postulado', 'entrevista', 'rechazado', 'contratado')"
    )

    op.create_table(
        "vacantes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "empresa_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column(
            "requisitos",
            ARRAY(sa.String(100)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("ubicacion", sa.String(180), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("activa", "pausada", "cerrada", name="vacante_estado", create_type=False),
            nullable=False,
            server_default="activa",
        ),
        sa.Column("categoria", sa.String(100)),
        sa.Column("salario_min", sa.Float),
        sa.Column("salario_max", sa.Float),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_vacantes_empresa_id", "vacantes", ["empresa_id"])
    op.create_index("ix_vacantes_ubicacion", "vacantes", ["ubicacion"])
    op.create_index("ix_vacantes_categoria", "vacantes", ["categoria"])
    op.create_index("ix_vacantes_estado", "vacantes", ["estado"])

    op.create_table(
        "postulaciones",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "candidato_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("perfiles_candidato.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vacante_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vacantes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "postulado", "entrevista", "rechazado", "contratado",
                name="postulacion_estado",
                create_type=False,
            ),
            nullable=False,
            server_default="postulado",
        ),
        sa.Column("score_match", sa.Float),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("candidato_id", "vacante_id", name="uq_candidato_vacante"),
    )
    op.create_index("ix_postulaciones_candidato_id", "postulaciones", ["candidato_id"])
    op.create_index("ix_postulaciones_vacante_id", "postulaciones", ["vacante_id"])


def downgrade() -> None:
    op.drop_index("ix_postulaciones_vacante_id", table_name="postulaciones")
    op.drop_index("ix_postulaciones_candidato_id", table_name="postulaciones")
    op.drop_table("postulaciones")

    op.drop_index("ix_vacantes_estado", table_name="vacantes")
    op.drop_index("ix_vacantes_categoria", table_name="vacantes")
    op.drop_index("ix_vacantes_ubicacion", table_name="vacantes")
    op.drop_index("ix_vacantes_empresa_id", table_name="vacantes")
    op.drop_table("vacantes")

    op.execute("DROP TYPE postulacion_estado")
    op.execute("DROP TYPE vacante_estado")
