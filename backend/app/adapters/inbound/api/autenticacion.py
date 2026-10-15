"""Endpoints de inicio y cierre de sesión (PB-01, RF-01)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app import config
from app.adapters.inbound.api.seguridad import (
    NOMBRE_COOKIE,
    UsuarioActual,
    get_servicio_autenticacion,
    ip_cliente,
    obtener_usuario_actual,
)
from app.adapters.outbound.seguridad.jwt_tokens import VIGENCIA
from app.application.autenticacion import (
    AccesoBloqueado,
    CredencialesInvalidas,
    ServicioAutenticacion,
)
from app.domain.autenticacion import VENTANA_BLOQUEO
from app.domain.usuarios import PermisoCodigo, RolNombre

router = APIRouter(prefix="/api/auth", tags=["autenticación"])

Servicio = Annotated[ServicioAutenticacion, Depends(get_servicio_autenticacion)]

MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos"
MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espera "
    f"{int(VENTANA_BLOQUEO.total_seconds() // 60)} minutos e inténtalo de nuevo."
)


class Credenciales(BaseModel):
    # str y no EmailStr: un correo mal escrito recibe la misma respuesta
    # genérica que una contraseña incorrecta, y queda en el historial.
    correo: str = Field(min_length=1, max_length=255)
    contrasena: str = Field(min_length=1, max_length=128)


class SesionSalida(BaseModel):
    id: UUID
    nombre: str
    correo: str
    rol: RolNombre
    permisos: list[PermisoCodigo]

    @classmethod
    def desde(cls, u: UsuarioActual) -> "SesionSalida":
        return cls(
            id=u.id, nombre=u.nombre, correo=u.correo, rol=u.rol, permisos=u.permisos
        )


@router.post("/login", response_model=SesionSalida)
def iniciar_sesion(
    datos: Credenciales, request: Request, response: Response, servicio: Servicio
):
    try:
        sesion = servicio.iniciar_sesion(
            datos.correo,
            datos.contrasena,
            ip=ip_cliente(request),
            user_agent=request.headers.get("user-agent"),
        )
    except CredencialesInvalidas:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, MENSAJE_CREDENCIALES
        ) from None
    except AccesoBloqueado:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            MENSAJE_BLOQUEO,
            headers={"Retry-After": str(int(VENTANA_BLOQUEO.total_seconds()))},
        ) from None

    response.set_cookie(
        NOMBRE_COOKIE,
        sesion.token,
        max_age=int(VIGENCIA.total_seconds()),
        httponly=True,
        secure=config.cookie_segura(),
        samesite="strict",
        path="/",
    )
    return SesionSalida.desde(UsuarioActual.desde(sesion.usuario))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def cerrar_sesion():
    respuesta = Response(status_code=status.HTTP_204_NO_CONTENT)
    respuesta.delete_cookie(
        NOMBRE_COOKIE,
        path="/",
        httponly=True,
        secure=config.cookie_segura(),
        samesite="strict",
    )
    return respuesta


@router.get("/yo", response_model=SesionSalida)
def sesion_actual(usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)]):
    return SesionSalida.desde(usuario)
