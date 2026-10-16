"""PC-16 diseñador de tabletop

Crea la sesión tabletop que diseña el moderador a partir de un escenario
publicado: sesion, sesion_rol, sesion_inject, sesion_tarea y
sesion_participante.

Las FK a escenario y usuario son RESTRICT: un escenario o una cuenta usados
en una sesión no se pueden eliminar, solo archivar o desactivar.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# Datos fijos de esta migración (no importar desde app/).
ESTADOS = ("borrador", "programada", "en_curso", "finalizada")
TIPOS_TAREA = ("texto_libre", "seleccion_multiple")


def _en(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    op.create_table(
        "sesion",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column(
            "escenario_id",
            sa.Uuid,
            sa.ForeignKey("escenario.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "moderador_id",
            sa.Uuid,
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("estado", sa.String(15), nullable=False, index=True),
        sa.Column("fecha_programada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duracion_minutos", sa.SmallInteger, nullable=True),
        sa.Column("peso_completitud", sa.SmallInteger, nullable=False),
        sa.Column("peso_precision", sa.SmallInteger, nullable=False),
        sa.Column("peso_tiempo", sa.SmallInteger, nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(f"estado IN ({_en(ESTADOS)})", name="ck_sesion_estado"),
        sa.CheckConstraint(
            "peso_completitud >= 0 AND peso_precision >= 0 AND peso_tiempo >= 0 "
            "AND peso_completitud + peso_precision + peso_tiempo = 100",
            name="ck_sesion_pesos",
        ),
        sa.CheckConstraint(
            "duracion_minutos IS NULL OR duracion_minutos > 0",
            name="ck_sesion_duracion",
        ),
    )
    op.create_table(
        "sesion_rol",
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "rol_codigo",
            sa.String(40),
            sa.ForeignKey("rol_ejercicio.codigo"),
            primary_key=True,
        ),
    )
    op.create_table(
        "sesion_inject",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("orden", sa.SmallInteger, nullable=False),
        sa.Column("titulo", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("minuto_sugerido", sa.SmallInteger, nullable=True),
        sa.UniqueConstraint("sesion_id", "orden"),
    )
    op.create_table(
        "sesion_tarea",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "inject_id",
            sa.Uuid,
            sa.ForeignKey("sesion_inject.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("posicion", sa.SmallInteger, nullable=False),
        sa.Column(
            "rol_codigo",
            sa.String(40),
            sa.ForeignKey("rol_ejercicio.codigo"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("enunciado", sa.Text, nullable=False),
        sa.Column("opciones", sa.JSON, nullable=False),
        sa.Column("criterios", sa.JSON, nullable=False),
        sa.Column("dificultad", sa.String(10), nullable=False),
        sa.Column("puntaje_maximo", sa.SmallInteger, nullable=False),
        sa.Column("tiempo_limite_segundos", sa.Integer, nullable=False),
        sa.Column("respuesta_esperada", sa.Text, nullable=True),
        sa.CheckConstraint(
            f"tipo IN ({_en(TIPOS_TAREA)})", name="ck_sesion_tarea_tipo"
        ),
        sa.CheckConstraint("puntaje_maximo > 0", name="ck_sesion_tarea_puntaje"),
    )
    op.create_table(
        "sesion_participante",
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "usuario_id",
            sa.Uuid,
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "rol_codigo",
            sa.String(40),
            sa.ForeignKey("rol_ejercicio.codigo"),
            nullable=False,
        ),
    )
    # Para buscar las sesiones de un participante (PB-06, PB-08).
    op.create_index(
        "ix_sesion_participante_usuario_id", "sesion_participante", ["usuario_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_sesion_participante_usuario_id", table_name="sesion_participante")
    op.drop_table("sesion_participante")
    op.drop_table("sesion_tarea")
    op.drop_table("sesion_inject")
    op.drop_table("sesion_rol")
    op.drop_table("sesion")
