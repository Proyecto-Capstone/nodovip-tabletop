"""PC-12 historial de accesos

Crea la tabla acceso: cada intento de login (usuario, fecha/hora, IP,
resultado) para RNF-01 y para el bloqueo por intentos fallidos.

`usuario_id` es RESTRICT: una cuenta con accesos registrados no se puede
eliminar, solo desactivar, para no perder la auditoría.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Datos fijos de esta migración (no importar desde app/).
RESULTADOS = ("exitoso", "credenciales_invalidas", "usuario_inactivo", "bloqueado")


def upgrade() -> None:
    valores = ", ".join(f"'{r}'" for r in RESULTADOS)
    op.create_table(
        "acceso",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Uuid,
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("correo_ingresado", sa.String(255), nullable=False),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("resultado", sa.String(30), nullable=False),
        sa.CheckConstraint(f"resultado IN ({valores})", name="ck_acceso_resultado"),
    )
    op.create_index(
        "ix_acceso_usuario_id_fecha_hora",
        "acceso",
        ["usuario_id", sa.text("fecha_hora DESC")],
    )
    op.create_index(
        "ix_acceso_correo_fecha_hora",
        "acceso",
        ["correo_ingresado", sa.text("fecha_hora DESC")],
    )
    op.create_index("ix_acceso_fecha_hora", "acceso", [sa.text("fecha_hora DESC")])


def downgrade() -> None:
    op.drop_index("ix_acceso_fecha_hora", table_name="acceso")
    op.drop_index("ix_acceso_correo_fecha_hora", table_name="acceso")
    op.drop_index("ix_acceso_usuario_id_fecha_hora", table_name="acceso")
    op.drop_table("acceso")
