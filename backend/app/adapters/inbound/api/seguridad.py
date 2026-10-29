"""Usuario actual y control de permisos para los endpoints (PB-01, RNF-01).

La sesión viaja en una cookie `httpOnly` con un JWT firmado. En cada request se
valida el token y se recarga el usuario de la base: si fue desactivado o le
cambiaron el rol, el cambio aplica de inmediato.

Los endpoints no dependen de cómo se autentica: siguen usando
`requiere_permiso(...)`.
"""

from dataclasses import dataclass
from functools import cache
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import config
from app.adapters.outbound.persistence.database import abrir_sesion, get_session
from app.adapters.outbound.persistence.repositorio_accesos import (
    SqlRegistroAccesoRepository,
)
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.adapters.outbound.seguridad.bcrypt_hasher import BcryptHasher
from app.adapters.outbound.seguridad.jwt_tokens import JwtTokens
from app.application.autenticacion import CLAVE_RELLENO, ServicioAutenticacion
from app.domain.usuarios import PERMISOS_POR_ROL, PermisoCodigo, RolNombre, Usuario

NOMBRE_COOKIE = "nodovip_sesion"


@dataclass(frozen=True)
class UsuarioActual:
    id: UUID
    nombre: str
    correo: str
    rol: RolNombre

    def puede(self, permiso: PermisoCodigo) -> bool:
        return permiso in PERMISOS_POR_ROL[self.rol]

    @property
    def permisos(self) -> list[PermisoCodigo]:
        return sorted(PERMISOS_POR_ROL[self.rol])

    @classmethod
    def desde(cls, u: Usuario) -> "UsuarioActual":
        return cls(id=u.id, nombre=u.nombre, correo=u.correo, rol=u.rol)


@cache
def _hash_relleno() -> str:
    """Hash bcrypt para igualar el tiempo de respuesta con correos inexistentes.
    Se calcula una sola vez por proceso (12 rondas tardan ~0,25 s)."""
    return BcryptHasher().hashear(CLAVE_RELLENO)


def get_servicio_autenticacion(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioAutenticacion:
    return ServicioAutenticacion(
        SqlUsuarioRepository(session),
        SqlRegistroAccesoRepository(session),
        BcryptHasher(),
        JwtTokens(config.jwt_secreto()),
        hash_relleno=_hash_relleno(),
    )


def ip_cliente(request: Request) -> str:
    """IP del cliente. Detrás de NGINX, uvicorn la toma de X-Forwarded-For
    (variable FORWARDED_ALLOW_IPS en docker-compose)."""
    return request.client.host if request.client else "desconocida"


def obtener_usuario_actual(
    servicio: Annotated[ServicioAutenticacion, Depends(get_servicio_autenticacion)],
    token: Annotated[str | None, Cookie(alias=NOMBRE_COOKIE)] = None,
) -> UsuarioActual:
    usuario = servicio.usuario_desde_token(token) if token else None
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
        )
    return UsuarioActual.desde(usuario)


def requiere_permiso(permiso: PermisoCodigo):
    """Dependencia de FastAPI: 403 si el rol del usuario no tiene el permiso."""

    def _verificar(
        usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
    ) -> UsuarioActual:
        if not usuario.puede(permiso):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return usuario

    return _verificar


def obtener_usuario_ws(
    token: Annotated[str | None, Cookie(alias=NOMBRE_COOKIE)] = None,
) -> UsuarioActual | None:
    """Usuario de un WebSocket (misma cookie que la API). None si no hay sesión.

    Abre y cierra su propia sesión de base de datos: el WebSocket puede durar
    horas y no debe retener una conexión del pool.
    """
    if not token:
        return None
    with abrir_sesion() as session:
        usuario = ServicioAutenticacion(
            SqlUsuarioRepository(session),
            SqlRegistroAccesoRepository(session),
            BcryptHasher(),
            JwtTokens(config.jwt_secreto()),
            hash_relleno=_hash_relleno(),
        ).usuario_desde_token(token)
    return UsuarioActual.desde(usuario) if usuario else None
