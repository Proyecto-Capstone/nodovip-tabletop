"""Entidades de dominio de usuarios, roles y permisos (M4).

Núcleo de dominio: no depende de FastAPI, SQLAlchemy ni de ningún framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class RolNombre(StrEnum):
    """Roles del sistema definidos en el documento Capstone."""

    ADMINISTRADOR = "administrador"
    MODERADOR = "moderador"
    PARTICIPANTE = "participante"
    OBSERVADOR = "observador"
    ANALISTA = "analista"


class PermisoCodigo(StrEnum):
    """Permisos del sistema. Cada rol recibe solo los que necesita (mínimo privilegio)."""

    USUARIOS_GESTIONAR = "usuarios:gestionar"
    ESCENARIOS_GESTIONAR = "escenarios:gestionar"
    ESCENARIOS_LEER = "escenarios:leer"
    SESIONES_DISENAR = "sesiones:disenar"
    SESIONES_CONDUCIR = "sesiones:conducir"
    SESIONES_PARTICIPAR = "sesiones:participar"
    SESIONES_MONITOREAR = "sesiones:monitorear"
    LEADERBOARD_VER = "leaderboard:ver"
    REPORTES_GENERAR = "reportes:generar"
    REPORTES_VER = "reportes:ver"


# Matriz rol → permisos. Ajustarla aquí y en la migración si cambia el documento.
PERMISOS_POR_ROL: dict[RolNombre, frozenset[PermisoCodigo]] = {
    RolNombre.ADMINISTRADOR: frozenset(
        {
            PermisoCodigo.USUARIOS_GESTIONAR,
            PermisoCodigo.ESCENARIOS_GESTIONAR,
            PermisoCodigo.ESCENARIOS_LEER,
            PermisoCodigo.SESIONES_MONITOREAR,
            PermisoCodigo.LEADERBOARD_VER,
            PermisoCodigo.REPORTES_VER,
        }
    ),
    RolNombre.MODERADOR: frozenset(
        {
            PermisoCodigo.ESCENARIOS_LEER,
            PermisoCodigo.SESIONES_DISENAR,
            PermisoCodigo.SESIONES_CONDUCIR,
            PermisoCodigo.LEADERBOARD_VER,
            PermisoCodigo.REPORTES_VER,
        }
    ),
    RolNombre.PARTICIPANTE: frozenset({PermisoCodigo.SESIONES_PARTICIPAR}),
    RolNombre.OBSERVADOR: frozenset({PermisoCodigo.LEADERBOARD_VER}),
    RolNombre.ANALISTA: frozenset(
        {PermisoCodigo.REPORTES_GENERAR, PermisoCodigo.REPORTES_VER}
    ),
}


@dataclass
class Usuario:
    correo: str
    nombre: str
    password_hash: str
    rol: RolNombre
    activo: bool = True
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime | None = None

    def tiene_permiso(self, permiso: PermisoCodigo) -> bool:
        return self.activo and permiso in PERMISOS_POR_ROL[self.rol]
