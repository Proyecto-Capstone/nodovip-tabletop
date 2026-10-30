"""Apoyo para las pruebas de integración contra PostgreSQL."""

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_respuestas import RespuestaModel


def purgar_respuestas(session: Session) -> None:
    """Borra las respuestas de la base de pruebas.

    El trigger de la migración 0008 impide borrarlas; solo lo permite si la
    transacción activa esta marca. Hay que hacer commit después.
    """
    session.execute(text("SET LOCAL nodovip.purgar_respuestas = 'si'"))
    session.execute(delete(RespuestaModel))
