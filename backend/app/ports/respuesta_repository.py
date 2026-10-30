"""Puerto de salida de las respuestas de los participantes (PB-08, PB-09).

Solo inserta y consulta: no hay operaciones para modificar ni borrar, y la
base de datos lo impide con un trigger (migración 0008).
"""

from typing import Protocol
from uuid import UUID

from app.domain.respuestas import Respuesta


class RespuestaDuplicada(Exception):
    """El participante ya respondió esa tarea (una sola respuesta por tarea)."""


class RespuestaRepository(Protocol):
    def guardar(self, respuesta: Respuesta) -> Respuesta:
        """Agrega la respuesta o lanza RespuestaDuplicada. Nunca modifica."""
        ...

    def de_participante(self, sesion_id: UUID, usuario_id: UUID) -> list[Respuesta]: ...

    def de_sesion(self, sesion_id: UUID) -> list[Respuesta]:
        """Todas las respuestas de la sesión en orden de llegada (PB-09)."""
        ...
