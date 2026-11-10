"""Apoyo para las pruebas de integración contra PostgreSQL."""

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_debrief import DebriefModel
from app.adapters.outbound.persistence.models_reportes import ReporteModel
from app.adapters.outbound.persistence.models_respuestas import (
    AjustePuntajeModel,
    RespuestaModel,
)


def purgar_respuestas(session: Session) -> None:
    """Borra las respuestas, los reportes y los debriefs de la base de pruebas, para poder
    borrar después las sesiones (todas sus FK son RESTRICT).

    Los triggers de las migraciones 0008 y 0009 impiden borrar las respuestas
    (y sus ajustes de puntaje); solo lo permiten si la transacción activa esta
    marca. Hay que hacer commit después.
    """
    session.execute(text("SET LOCAL nodovip.purgar_respuestas = 'si'"))
    session.execute(delete(ReporteModel))
    session.execute(delete(DebriefModel))
    session.execute(delete(AjustePuntajeModel))
    session.execute(delete(RespuestaModel))
