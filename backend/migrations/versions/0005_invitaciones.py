"""PC-17 invitaciones a las sesiones

Agrega a sesion_participante el seguimiento de la invitación por correo:
estado (pendiente, enviada, fallida, aceptada), fechas de envío y aceptación y
el último error del proveedor (Brevo).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Datos fijos de esta migración (no importar desde app/).
ESTADOS = ("pendiente", "enviada", "fallida", "aceptada")


def upgrade() -> None:
    valores = ", ".join(f"'{e}'" for e in ESTADOS)
    # Las filas existentes quedan "pendiente": nunca se les envió correo.
    op.add_column(
        "sesion_participante",
        sa.Column(
            "invitacion",
            sa.String(15),
            nullable=False,
            server_default="pendiente",
        ),
    )
    op.add_column(
        "sesion_participante",
        sa.Column("invitacion_enviada_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sesion_participante",
        sa.Column("invitacion_aceptada_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sesion_participante",
        sa.Column("invitacion_error", sa.String(300), nullable=True),
    )
    op.create_check_constraint(
        "ck_sesion_participante_invitacion",
        "sesion_participante",
        f"invitacion IN ({valores})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sesion_participante_invitacion", "sesion_participante", type_="check"
    )
    op.drop_column("sesion_participante", "invitacion_error")
    op.drop_column("sesion_participante", "invitacion_aceptada_en")
    op.drop_column("sesion_participante", "invitacion_enviada_en")
    op.drop_column("sesion_participante", "invitacion")
