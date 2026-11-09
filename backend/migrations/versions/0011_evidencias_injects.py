"""PC-44 evidencia simulada en los injects

`inject.evidencia` y `sesion_inject.evidencia`: artefacto ficticio que acompaña
al inject (correo, alerta del SIEM, noticia, llamada, mensaje o documento) para
que el participante lo vea como en un incidente real. JSON con tipo, origen,
asunto, contenido y nivel (solo alertas). Opcional: los injects existentes
quedan sin evidencia.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inject", sa.Column("evidencia", sa.JSON, nullable=True))
    op.add_column("sesion_inject", sa.Column("evidencia", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("sesion_inject", "evidencia")
    op.drop_column("inject", "evidencia")
