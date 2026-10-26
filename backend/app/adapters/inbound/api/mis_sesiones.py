"""Endpoints del participante: sus sesiones y la aceptación de la invitación (PB-06).

Permiso `sesiones:participar`. Una sesión a la que el usuario no fue invitado
(o que todavía es borrador) responde 404: no se revela que existe. No expone
tareas, opciones ni criterios: el participante los recibe en vivo (PB-08).
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.correo import crear_enviador
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import (
    SqlSesionRepository,
)
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.invitaciones import ServicioInvitaciones, SesionDelParticipante
from app.application.sesiones import SesionNoEncontrada
from app.domain.sesiones import EstadoInvitacion, EstadoSesion, ReglaSesionError
from app.domain.usuarios import PermisoCodigo

router = APIRouter(prefix="/api/mis-sesiones", tags=["participante"])


def get_servicio(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioInvitaciones:
    return ServicioInvitaciones(
        SqlSesionRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
        crear_enviador(),
        config.url_aplicacion(),
        escenarios=SqlEscenarioRepository(session),
    )


Servicio = Annotated[ServicioInvitaciones, Depends(get_servicio)]
Participante = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_PARTICIPAR))
]


class SesionDelParticipanteSalida(BaseModel):
    id: UUID
    nombre: str
    estado: EstadoSesion
    fecha_programada: datetime | None
    duracion_minutos: int | None
    escenario_nombre: str
    escenario_descripcion: str
    moderador_nombre: str
    rol_codigo: str
    rol_nombre: str
    total_participantes: int
    invitacion: EstadoInvitacion
    invitacion_aceptada_en: datetime | None

    @classmethod
    def desde(cls, v: SesionDelParticipante) -> "SesionDelParticipanteSalida":
        return cls(
            id=v.sesion.id,
            nombre=v.sesion.nombre,
            estado=v.sesion.estado,
            fecha_programada=v.sesion.fecha_programada,
            duracion_minutos=v.sesion.duracion_minutos,
            escenario_nombre=v.escenario_nombre,
            escenario_descripcion=v.escenario_descripcion,
            moderador_nombre=v.moderador_nombre,
            rol_codigo=v.participante.rol_codigo,
            rol_nombre=v.rol_nombre,
            total_participantes=len(v.sesion.participantes),
            invitacion=v.participante.invitacion,
            invitacion_aceptada_en=v.participante.invitacion_aceptada_en,
        )


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada") from None
    except ReglaSesionError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e


@router.get("", response_model=list[SesionDelParticipanteSalida])
def mis_sesiones(servicio: Servicio, usuario: Participante):
    return [
        SesionDelParticipanteSalida.desde(v) for v in servicio.mis_sesiones(usuario.id)
    ]


@router.get("/{sesion_id}", response_model=SesionDelParticipanteSalida)
def mi_sesion(sesion_id: UUID, servicio: Servicio, usuario: Participante):
    vista = _manejar_errores(lambda: servicio.obtener(sesion_id, usuario.id))
    return SesionDelParticipanteSalida.desde(vista)


@router.post("/{sesion_id}/aceptar", response_model=SesionDelParticipanteSalida)
def aceptar_invitacion(sesion_id: UUID, servicio: Servicio, usuario: Participante):
    vista = _manejar_errores(lambda: servicio.aceptar(sesion_id, usuario.id))
    return SesionDelParticipanteSalida.desde(vista)
