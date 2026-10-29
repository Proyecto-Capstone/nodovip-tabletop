"""PC-19 respuestas de los participantes

Crea la tabla respuesta: una por participante y tarea (UNIQUE), con la hora
del servidor y los segundos efectivos que usó. Todas las FK son RESTRICT: una
respuesta registrada impide borrar la sesión, la tarea o el usuario.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "respuesta",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tarea_id",
            sa.Uuid,
            sa.ForeignKey("sesion_tarea.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "inject_id",
            sa.Uuid,
            sa.ForeignKey("sesion_inject.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.Uuid,
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "rol_codigo",
            sa.String(40),
            sa.ForeignKey("rol_ejercicio.codigo"),
            nullable=False,
        ),
        sa.Column("texto", sa.Text, nullable=True),
        sa.Column("opciones_elegidas", sa.JSON, nullable=False),
        sa.Column("recibida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("segundos_usados", sa.Integer, nullable=False),
        sa.UniqueConstraint(
            "tarea_id", "usuario_id", name="uq_respuesta_tarea_usuario"
        ),
        sa.CheckConstraint("segundos_usados >= 0", name="ck_respuesta_segundos"),
    )
    # Respuestas de un participante en una sesión (su vista y el reporte).
    op.create_index(
        "ix_respuesta_sesion_usuario", "respuesta", ["sesion_id", "usuario_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_respuesta_sesion_usuario", table_name="respuesta")
    op.drop_table("respuesta")
