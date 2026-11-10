"""PC-45 debrief y lecciones aprendidas

`debrief`: uno por sesión finalizada. Fortalezas, aspectos a mejorar y plan de
acción (JSON: descripción, prioridad, rol responsable y plazo). Estado borrador
o completado; el completado pasa al reporte de brechas.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debrief",
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "autor_id",
            sa.Uuid,
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("fortalezas", sa.JSON, nullable=False),
        sa.Column("mejoras", sa.JSON, nullable=False),
        sa.Column("acciones", sa.JSON, nullable=False),
        # borrador | completado
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('borrador', 'completado')", name="ck_debrief_estado"
        ),
    )


def downgrade() -> None:
    op.drop_table("debrief")
