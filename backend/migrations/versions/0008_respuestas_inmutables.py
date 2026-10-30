"""PC-20 respuestas inmutables a nivel de base de datos

Un trigger rechaza todo UPDATE, DELETE y TRUNCATE sobre la tabla respuesta:
una respuesta registrada es evidencia auditable y no cambia nunca, aunque
alguien acceda a la base sin pasar por la API.

La única excepción es la purga controlada (DELETE o TRUNCATE, nunca UPDATE)
cuando la transacción activa `SET LOCAL nodovip.purgar_respuestas = 'si'`.
La usan las pruebas de integración para limpiar su base; en producción solo un
administrador de la base podría hacerlo, a propósito y por SQL.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-30
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION respuesta_inmutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP <> 'UPDATE'
               AND current_setting('nodovip.purgar_respuestas', true) = 'si' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION
                'Las respuestas registradas no se pueden modificar ni borrar'
                USING ERRCODE = 'integrity_constraint_violation',
                      HINT = 'Tabla de solo inserción (PB-09, trazabilidad)';
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER tr_respuesta_inmutable
        BEFORE UPDATE OR DELETE ON respuesta
        FOR EACH ROW EXECUTE FUNCTION respuesta_inmutable();
        """
    )
    op.execute(
        """
        CREATE TRIGGER tr_respuesta_sin_truncate
        BEFORE TRUNCATE ON respuesta
        FOR EACH STATEMENT EXECUTE FUNCTION respuesta_inmutable();
        """
    )
    # Consulta por sesión en orden de llegada (panel PB-11 y reporte PB-14).
    op.create_index(
        "ix_respuesta_sesion_recibida", "respuesta", ["sesion_id", "recibida_en"]
    )


def downgrade() -> None:
    op.drop_index("ix_respuesta_sesion_recibida", table_name="respuesta")
    op.execute("DROP TRIGGER tr_respuesta_sin_truncate ON respuesta")
    op.execute("DROP TRIGGER tr_respuesta_inmutable ON respuesta")
    op.execute("DROP FUNCTION respuesta_inmutable()")
