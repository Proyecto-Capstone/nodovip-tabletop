"""PC-25 cliente de la sesión y reporte PDF de brechas

- `sesion.cliente`: organización para la que se hace el ejercicio. El reporte
  compara con las sesiones finalizadas anteriores del mismo cliente. Opcional:
  las sesiones existentes quedan sin cliente.
- `reporte`: el último PDF generado de cada sesión (uno por sesión). Se genera
  en segundo plano al cerrar la sesión y se puede regenerar (por ejemplo,
  después de ajustar puntajes), así que no es de solo inserción.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sesion", sa.Column("cliente", sa.String(120), nullable=True))
    op.create_index("ix_sesion_cliente", "sesion", ["cliente"])

    op.create_table(
        "reporte",
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        # generando | generado | fallido
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("solicitado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf", sa.LargeBinary, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.CheckConstraint(
            "estado IN ('generando', 'generado', 'fallido')", name="ck_reporte_estado"
        ),
    )


def downgrade() -> None:
    op.drop_table("reporte")
    op.drop_index("ix_sesion_cliente", table_name="sesion")
    op.drop_column("sesion", "cliente")
