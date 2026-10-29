"""PC-18 ejecución en vivo de la sesión

Agrega a sesion los datos de su ejecución: cuándo se inició, cuándo terminó y
el último inject lanzado. El estado activo vive en Redis; estas columnas
permiten reconstruirlo si Redis se pierde y quedan como registro de la sesión.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sesion", sa.Column("iniciada_en", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "sesion", sa.Column("finalizada_en", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "sesion",
        sa.Column("inject_actual", sa.SmallInteger, nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_sesion_inject_actual", "sesion", "inject_actual >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_sesion_inject_actual", "sesion", type_="check")
    op.drop_column("sesion", "inject_actual")
    op.drop_column("sesion", "finalizada_en")
    op.drop_column("sesion", "iniciada_en")
