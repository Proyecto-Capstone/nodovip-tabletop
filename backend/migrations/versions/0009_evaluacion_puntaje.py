"""PC-21 evaluación automática y ajustes manuales de puntaje

- `respuesta` guarda el resultado del evaluador al recibirla (puntaje, máximo,
  los tres aspectos y el detalle). Como la fila es inmutable (0008), el puntaje
  automático original queda como evidencia. Son NULL en respuestas anteriores.
- `ajuste_puntaje`: cada cambio manual del moderador, con el puntaje anterior,
  el nuevo, el motivo, quién y cuándo. Solo inserción, igual que `respuesta`
  (misma purga controlada para las pruebas).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

ASPECTO = sa.Numeric(4, 3)
PUNTAJE = sa.Numeric(6, 2)


def upgrade() -> None:
    op.add_column("respuesta", sa.Column("puntaje_automatico", PUNTAJE))
    op.add_column("respuesta", sa.Column("puntaje_maximo", sa.SmallInteger))
    op.add_column("respuesta", sa.Column("eval_completitud", ASPECTO))
    op.add_column("respuesta", sa.Column("eval_precision", ASPECTO))
    op.add_column("respuesta", sa.Column("eval_tiempo", ASPECTO))
    # {"aciertos": [...], "faltantes": [...], "errores": [...]}
    op.add_column("respuesta", sa.Column("eval_detalle", sa.JSON))

    op.create_table(
        "ajuste_puntaje",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "respuesta_id",
            sa.Uuid,
            sa.ForeignKey("respuesta.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sesion_id",
            sa.Uuid,
            sa.ForeignKey("sesion.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "moderador_id",
            sa.Uuid,
            sa.ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("puntaje_anterior", PUNTAJE, nullable=False),
        sa.Column("puntaje_nuevo", PUNTAJE, nullable=False),
        sa.Column("motivo", sa.Text, nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("puntaje_nuevo >= 0", name="ck_ajuste_puntaje_nuevo"),
        sa.CheckConstraint("length(trim(motivo)) >= 5", name="ck_ajuste_motivo"),
    )
    op.create_index(
        "ix_ajuste_puntaje_sesion", "ajuste_puntaje", ["sesion_id", "creado_en"]
    )
    op.execute(
        """
        CREATE FUNCTION ajuste_inmutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP <> 'UPDATE'
               AND current_setting('nodovip.purgar_respuestas', true) = 'si' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION
                'Los ajustes de puntaje no se pueden modificar ni borrar'
                USING ERRCODE = 'integrity_constraint_violation',
                      HINT = 'Registra un ajuste nuevo (PB-10, historial)';
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER tr_ajuste_inmutable
        BEFORE UPDATE OR DELETE ON ajuste_puntaje
        FOR EACH ROW EXECUTE FUNCTION ajuste_inmutable();
        """
    )
    op.execute(
        """
        CREATE TRIGGER tr_ajuste_sin_truncate
        BEFORE TRUNCATE ON ajuste_puntaje
        FOR EACH STATEMENT EXECUTE FUNCTION ajuste_inmutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER tr_ajuste_sin_truncate ON ajuste_puntaje")
    op.execute("DROP TRIGGER tr_ajuste_inmutable ON ajuste_puntaje")
    op.execute("DROP FUNCTION ajuste_inmutable()")
    op.drop_index("ix_ajuste_puntaje_sesion", table_name="ajuste_puntaje")
    op.drop_table("ajuste_puntaje")
    for columna in (
        "eval_detalle",
        "eval_tiempo",
        "eval_precision",
        "eval_completitud",
        "puntaje_maximo",
        "puntaje_automatico",
    ):
        op.drop_column("respuesta", columna)
