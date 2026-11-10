"""PC-46 selección múltiple e inject de cada tarea del escenario

- `tarea.tipo` (texto_libre | seleccion_multiple) y `tarea.opciones` (JSON con
  texto y si es correcta). Las tareas existentes quedan como texto libre.
- `tarea.inject_orden`: en qué inject del escenario se pregunta. Sin valor, la
  sesión las reparte en orden como antes.

Al crear una sesión desde el escenario, todo se copia a `sesion_tarea`.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tarea",
        sa.Column("tipo", sa.String(20), nullable=False, server_default="texto_libre"),
    )
    op.add_column(
        "tarea",
        sa.Column("opciones", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("tarea", sa.Column("inject_orden", sa.SmallInteger, nullable=True))
    op.create_check_constraint(
        "ck_tarea_tipo", "tarea", "tipo IN ('texto_libre', 'seleccion_multiple')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_tarea_tipo", "tarea", type_="check")
    op.drop_column("tarea", "inject_orden")
    op.drop_column("tarea", "opciones")
    op.drop_column("tarea", "tipo")
