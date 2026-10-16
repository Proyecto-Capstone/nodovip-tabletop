"""Endpoints REST de gestión de usuarios y roles (PB-02). Solo Administrador."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.adapters.outbound.seguridad.bcrypt_hasher import BcryptHasher
from app.application.usuarios import (
    CorreoDuplicado,
    ServicioUsuarios,
    UsuarioNoEncontrado,
)
from app.domain.usuarios import (
    PermisoCodigo,
    ReglaUsuarioError,
    RolNombre,
    Usuario,
)
from app.ports.usuario_repository import FiltroUsuarios

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


def get_servicio_usuarios(
    session: Annotated[Session, Depends(get_session)],
) -> Iterator[ServicioUsuarios]:
    yield ServicioUsuarios(SqlUsuarioRepository(session), BcryptHasher())


Servicio = Annotated[ServicioUsuarios, Depends(get_servicio_usuarios)]
Administrador = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.USUARIOS_GESTIONAR))
]


# --- Esquemas ---------------------------------------------------------------------


class UsuarioCrear(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=150)
    correo: EmailStr = Field(max_length=255)
    contrasena: str = Field(min_length=1, max_length=128)
    rol: RolNombre


class UsuarioActualizar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=150)
    correo: EmailStr = Field(max_length=255)
    rol: RolNombre


class NuevaContrasena(BaseModel):
    contrasena: str = Field(min_length=1, max_length=128)


class UsuarioSalida(BaseModel):
    """Nunca incluye el hash de la contraseña."""

    id: UUID
    nombre: str
    correo: str
    rol: RolNombre
    activo: bool
    creado_en: datetime | None

    @classmethod
    def desde(cls, u: Usuario) -> "UsuarioSalida":
        return cls(
            id=u.id,
            nombre=u.nombre,
            correo=u.correo,
            rol=u.rol,
            activo=u.activo,
            creado_en=u.creado_en,
        )


def _ejecutar(funcion):
    try:
        return UsuarioSalida.desde(funcion())
    except UsuarioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Usuario no encontrado"
        ) from None
    except (CorreoDuplicado, IntegrityError):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"errores": ["Ya existe un usuario con ese correo"]},
        ) from None
    except ReglaUsuarioError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e


# --- Endpoints --------------------------------------------------------------------


@router.get("", response_model=list[UsuarioSalida])
def listar_usuarios(
    servicio: Servicio,
    _: Administrador,
    q: Annotated[str | None, Query(max_length=100)] = None,
    rol: RolNombre | None = None,
    activo: bool | None = None,
):
    filtro = FiltroUsuarios(texto=q, rol=rol, activo=activo)
    return [UsuarioSalida.desde(u) for u in servicio.listar(filtro)]


@router.get("/{usuario_id}", response_model=UsuarioSalida)
def obtener_usuario(usuario_id: UUID, servicio: Servicio, _: Administrador):
    return _ejecutar(lambda: servicio.obtener(usuario_id))


@router.post("", response_model=UsuarioSalida, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioCrear, servicio: Servicio, _: Administrador):
    return _ejecutar(
        lambda: servicio.crear(datos.nombre, datos.correo, datos.contrasena, datos.rol)
    )


@router.put("/{usuario_id}", response_model=UsuarioSalida)
def actualizar_usuario(
    usuario_id: UUID, datos: UsuarioActualizar, servicio: Servicio, _: Administrador
):
    return _ejecutar(
        lambda: servicio.actualizar(usuario_id, datos.nombre, datos.correo, datos.rol)
    )


@router.post("/{usuario_id}/desactivar", response_model=UsuarioSalida)
def desactivar_usuario(usuario_id: UUID, servicio: Servicio, _: Administrador):
    return _ejecutar(lambda: servicio.desactivar(usuario_id))


@router.post("/{usuario_id}/activar", response_model=UsuarioSalida)
def activar_usuario(usuario_id: UUID, servicio: Servicio, _: Administrador):
    return _ejecutar(lambda: servicio.activar(usuario_id))


@router.post("/{usuario_id}/contrasena", response_model=UsuarioSalida)
def restablecer_contrasena(
    usuario_id: UUID, datos: NuevaContrasena, servicio: Servicio, _: Administrador
):
    return _ejecutar(
        lambda: servicio.restablecer_contrasena(usuario_id, datos.contrasena)
    )


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: UUID, servicio: Servicio, _: Administrador):
    try:
        servicio.eliminar(usuario_id)
    except UsuarioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Usuario no encontrado"
        ) from None
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "errores": [
                    (
                        "El usuario tiene registros asociados (accesos, sesiones "
                        "o respuestas) y no se puede eliminar; déjalo desactivado"
                    )
                ]
            },
        ) from None
    except ReglaUsuarioError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)
