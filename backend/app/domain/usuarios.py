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


# --- Reglas de gestión de usuarios (PB-02, RF-05) -----------------------------

CONTRASENA_MIN = 10
# bcrypt solo usa los primeros 72 bytes; más largo se rechaza para no truncar.
CONTRASENA_MAX_BYTES = 72


class ReglaUsuarioError(ValueError):
    """Un dato de usuario no cumple una regla de negocio."""

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("; ".join(errores))


def normalizar_correo(correo: str) -> str:
    """El correo es el dato de login: se compara sin espacios y en minúsculas."""
    return correo.strip().lower()


def errores_contrasena(contrasena: str) -> list[str]:
    """Política mínima de contraseñas. Devuelve la lista de reglas incumplidas."""
    errores: list[str] = []
    if len(contrasena) < CONTRASENA_MIN:
        errores.append(f"Debe tener al menos {CONTRASENA_MIN} caracteres")
    if len(contrasena.encode("utf-8")) > CONTRASENA_MAX_BYTES:
        errores.append("Es demasiado larga (máximo 72 bytes)")
    if not any(c.islower() for c in contrasena):
        errores.append("Debe incluir al menos una letra minúscula")
    if not any(c.isupper() for c in contrasena):
        errores.append("Debe incluir al menos una letra mayúscula")
    if not any(c.isdigit() for c in contrasena):
        errores.append("Debe incluir al menos un número")
    if contrasena != contrasena.strip():
        errores.append("No puede empezar ni terminar con espacios")
    return errores


def validar_contrasena(contrasena: str) -> None:
    errores = errores_contrasena(contrasena)
    if errores:
        raise ReglaUsuarioError([f"Contraseña: {e.lower()}" for e in errores])
