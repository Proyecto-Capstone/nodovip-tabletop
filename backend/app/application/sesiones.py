"""Casos de uso del diseñador de tabletop (PB-05, RF-01).

Coordina dominio y puertos. No conoce HTTP ni SQLAlchemy.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.domain.escenarios import EstadoEscenario
from app.domain.sesiones import EstadoSesion, ReglaSesionError, SesionTabletop
from app.domain.usuarios import RolNombre, Usuario
from app.ports.escenario_repository import CatalogoRepository, EscenarioRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import FiltroUsuarios, UsuarioRepository


class SesionNoEncontrada(LookupError):
    pass


def _ahora() -> datetime:
    return datetime.now(UTC)


class ServicioSesiones:
    def __init__(
        self,
        repo: SesionRepository,
        escenarios: EscenarioRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.repo = repo
        self.escenarios = escenarios
        self.catalogo = catalogo
        self.usuarios = usuarios
        self.reloj = reloj

    def crear(
        self, escenario_id: UUID, moderador_id: UUID, nombre: str | None = None
    ) -> SesionTabletop:
        """Paso 1 del diseñador: el borrador nace de un escenario publicado."""
        escenario = self.escenarios.obtener(escenario_id)
        if escenario is None or escenario.estado != EstadoEscenario.PUBLICADO:
            raise ReglaSesionError(["El escenario no existe o no está publicado"])
        sesion = SesionTabletop.desde_escenario(escenario, moderador_id, nombre)
        return self.repo.guardar(sesion)

    def listar(self, moderador_id: UUID) -> list[SesionTabletop]:
        return self.repo.listar_por_moderador(moderador_id)

    def obtener(self, sesion_id: UUID, moderador_id: UUID) -> SesionTabletop:
        """Cada moderador solo ve las sesiones que diseñó."""
        sesion = self.repo.obtener(sesion_id)
        if sesion is None or sesion.moderador_id != moderador_id:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion

    def actualizar(
        self, sesion_id: UUID, moderador_id: UUID, nuevo: SesionTabletop
    ) -> SesionTabletop:
        """Guarda el diseño (borrador o cambios a una sesión programada)."""
        sesion = self.obtener(sesion_id, moderador_id)
        self._validar_roles(nuevo.roles)
        self._validar_participantes(nuevo)
        sesion.reemplazar_diseno(nuevo, self.reloj())
        return self.repo.guardar(sesion)

    def programar(self, sesion_id: UUID, moderador_id: UUID) -> SesionTabletop:
        sesion = self.obtener(sesion_id, moderador_id)
        self._validar_participantes(sesion)
        sesion.programar(self.reloj())
        return self.repo.guardar(sesion)

    def eliminar(self, sesion_id: UUID, moderador_id: UUID) -> None:
        sesion = self.obtener(sesion_id, moderador_id)
        if sesion.estado != EstadoSesion.BORRADOR:
            raise ReglaSesionError(["Solo se pueden eliminar sesiones en borrador"])
        self.repo.eliminar(sesion.id)

    def participantes_disponibles(self) -> list[Usuario]:
        """Usuarios que se pueden asignar a un rol: participantes activos."""
        return self.usuarios.listar(
            FiltroUsuarios(rol=RolNombre.PARTICIPANTE, activo=True)
        )

    # --- apoyo ----------------------------------------------------------------

    def _validar_roles(self, roles: list[str]) -> None:
        conocidos = {r.codigo for r in self.catalogo.roles_ejercicio()}
        desconocidos = sorted(set(roles) - conocidos)
        if desconocidos:
            raise ReglaSesionError(["Roles desconocidos: " + ", ".join(desconocidos)])

    def _validar_participantes(self, sesion: SesionTabletop) -> None:
        """Se revisa también al programar: el usuario pudo desactivarse."""
        invalidos = []
        for p in sesion.participantes:
            usuario = self.usuarios.obtener_por_id(p.usuario_id)
            if (
                usuario is None
                or not usuario.activo
                or usuario.rol != RolNombre.PARTICIPANTE
            ):
                invalidos.append(str(p.usuario_id))
        if invalidos:
            raise ReglaSesionError(
                [
                    "Solo se pueden asignar participantes activos: "
                    + ", ".join(invalidos)
                ]
            )
