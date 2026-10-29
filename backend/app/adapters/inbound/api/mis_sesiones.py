"""Endpoints del participante: sus sesiones, la aceptación de la invitación
(PB-06) y las tareas de su rol con su respuesta (PB-08).

Permiso `sesiones:participar`. Una sesión a la que el usuario no fue invitado
(o que todavía es borrador) responde 404: no se revela que existe. No expone
tareas, opciones ni criterios: el participante los recibe en vivo (PB-08).
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import config
from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.correo import crear_enviador
from app.adapters.outbound.en_vivo import adaptador_en_vivo
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_respuestas import (
    SqlRespuestaRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import (
    SqlSesionRepository,
)
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.invitaciones import ServicioInvitaciones, SesionDelParticipante
from app.application.respuestas import (
    ServicioRespuestas,
    TareaDelParticipante,
    TareaNoEncontrada,
)
from app.application.sesiones import SesionNoEncontrada
from app.domain.respuestas import EstadoTarea
from app.domain.sesiones import (
    EstadoInvitacion,
    EstadoSesion,
    ReglaSesionError,
    TipoTarea,
)
from app.domain.usuarios import PermisoCodigo
from app.ports.respuesta_repository import RespuestaDuplicada

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
    except TareaNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada") from None
    except RespuestaDuplicada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya respondiste esta tarea: no se puede cambiar"
        ) from None
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


# --- Tareas y respuestas (PB-08) ------------------------------------------------------


def get_servicio_respuestas(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioRespuestas:
    return ServicioRespuestas(
        SqlSesionRepository(session),
        adaptador_en_vivo(),
        SqlRespuestaRepository(session),
    )


Respuestas = Annotated[ServicioRespuestas, Depends(get_servicio_respuestas)]


class MiRespuestaSalida(BaseModel):
    texto: str | None
    opciones_elegidas: list[int]
    recibida_en: datetime


class TareaParticipanteSalida(BaseModel):
    """Lo que ve el participante: sin la opción correcta ni los criterios."""

    id: UUID
    inject_orden: int
    tipo: TipoTarea
    enunciado: str
    opciones: list[str]
    tiempo_limite_segundos: int
    segundos_restantes: int
    estado: EstadoTarea
    respuesta: MiRespuestaSalida | None

    @classmethod
    def desde(cls, t: TareaDelParticipante) -> "TareaParticipanteSalida":
        return cls(
            id=t.tarea.id,
            inject_orden=t.inject_orden,
            tipo=t.tarea.tipo,
            enunciado=t.tarea.enunciado,
            opciones=[o.texto for o in t.tarea.opciones],
            tiempo_limite_segundos=t.tarea.tiempo_limite_segundos,
            segundos_restantes=t.segundos_restantes,
            estado=t.estado,
            respuesta=MiRespuestaSalida(
                texto=t.respuesta.texto,
                opciones_elegidas=t.respuesta.opciones_elegidas,
                recibida_en=t.respuesta.recibida_en,
            )
            if t.respuesta
            else None,
        )


class RespuestaEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    texto: str | None = Field(default=None, max_length=5000)
    opciones: list[int] = Field(default_factory=list, max_length=8)


@router.get("/{sesion_id}/tareas", response_model=list[TareaParticipanteSalida])
def mis_tareas(sesion_id: UUID, servicio: Respuestas, usuario: Participante):
    tareas = _manejar_errores(lambda: servicio.tareas(sesion_id, usuario.id))
    return [TareaParticipanteSalida.desde(t) for t in tareas]


@router.post(
    "/{sesion_id}/tareas/{tarea_id}/respuesta",
    response_model=TareaParticipanteSalida,
    status_code=status.HTTP_201_CREATED,
)
def responder_tarea(
    sesion_id: UUID,
    tarea_id: UUID,
    datos: RespuestaEntrada,
    servicio: Respuestas,
    usuario: Participante,
):
    """Una sola vez por tarea y dentro del tiempo límite (409 / 422 si no)."""

    def responder():
        servicio.responder(sesion_id, usuario.id, tarea_id, datos.texto, datos.opciones)
        return next(
            t for t in servicio.tareas(sesion_id, usuario.id) if t.tarea.id == tarea_id
        )

    return TareaParticipanteSalida.desde(_manejar_errores(responder))
