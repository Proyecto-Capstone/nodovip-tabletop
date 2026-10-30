"""Puertos de salida del diseño de sesiones tabletop (M1)."""

from typing import Protocol
from uuid import UUID

from app.domain.sesiones import EstadoSesion, SesionTabletop


class SesionRepository(Protocol):
    def obtener(self, sesion_id: UUID) -> SesionTabletop | None: ...

    def listar_por_moderador(self, moderador_id: UUID) -> list[SesionTabletop]: ...

    def listar_por_participante(self, usuario_id: UUID) -> list[SesionTabletop]:
        """Sesiones en las que el usuario está invitado, de cualquier estado."""
        ...

    def listar_por_estados(
        self, estados: tuple[EstadoSesion, ...]
    ) -> list[SesionTabletop]:
        """Todas las sesiones en alguno de esos estados (PB-12: leaderboard)."""
        ...

    def guardar(self, sesion: SesionTabletop) -> SesionTabletop: ...

    def eliminar(self, sesion_id: UUID) -> None: ...
