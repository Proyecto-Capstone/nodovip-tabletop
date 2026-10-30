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

    def iniciar_si_hay_cupo(
        self, sesion: SesionTabletop, maximo_activas: int
    ) -> SesionTabletop | None:
        """Guarda `sesion` (ya en estado EN_CURSO) solo si hay cupo (PC-24,
        RNF). Cuenta las sesiones EN_CURSO y guarda en una única operación
        atómica, para que dos arranques simultáneos no superen
        `maximo_activas`. Devuelve `None` sin guardar si ya se alcanzó el
        máximo."""
        ...

    def eliminar(self, sesion_id: UUID) -> None: ...
