"""Puertos de salida de la autenticación (PB-01).

El caso de uso depende de estas interfaces, nunca de SQLAlchemy ni de PyJWT.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.autenticacion import RegistroAcceso, ResultadoAcceso


@dataclass
class FiltroAccesos:
    usuario_id: UUID | None = None
    correo: str | None = None
    resultado: ResultadoAcceso | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    limite: int = 200


class RegistroAccesoRepository(Protocol):
    def registrar(self, registro: RegistroAcceso) -> None: ...

    def resultados_recientes(
        self, correo: str, desde: datetime, limite: int
    ) -> list[ResultadoAcceso]:
        """Resultados de los intentos con ese correo desde `desde`, del más
        reciente al más antiguo, sin contar los `bloqueado` (si contaran,
        seguir intentando durante el bloqueo sacaría del límite los fallos
        que lo causaron)."""
        ...

    def listar(self, filtro: FiltroAccesos) -> list[RegistroAcceso]: ...


class EmisorTokens(Protocol):
    def emitir(self, usuario_id: UUID) -> str: ...

    def validar(self, token: str) -> UUID | None:
        """Devuelve el id del usuario o None si el token es inválido o venció."""
        ...
