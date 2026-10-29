"""Puerto de salida de las respuestas de los participantes (PB-08)."""

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
