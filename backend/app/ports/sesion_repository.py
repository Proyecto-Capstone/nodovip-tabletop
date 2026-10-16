"""Puertos de salida del diseño de sesiones tabletop (M1)."""

from typing import Protocol
from uuid import UUID

from app.domain.sesiones import SesionTabletop


class SesionRepository(Protocol):
    def obtener(self, sesion_id: UUID) -> SesionTabletop | None: ...

    def listar_por_moderador(self, moderador_id: UUID) -> list[SesionTabletop]: ...

    def guardar(self, sesion: SesionTabletop) -> SesionTabletop: ...

    def eliminar(self, sesion_id: UUID) -> None: ...
