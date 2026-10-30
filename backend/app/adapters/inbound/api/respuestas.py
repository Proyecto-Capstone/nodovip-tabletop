"""Registro trazable de respuestas (PB-09, RF-07) y su puntaje (PB-10, RF-03).

Para el moderador dueño de la sesión (permiso `sesiones:conducir`):

- `GET /api/sesiones/{id}/respuestas`: registro en orden de llegada, con el
  puntaje automático, el vigente y el historial de ajustes.
- `POST /api/sesiones/{id}/respuestas/{respuesta_id}/ajustes`: ajuste manual
  con motivo. No modifica la respuesta: agrega un registro.
- `GET /api/sesiones/{id}/puntajes`: acumulado por participante y por rol.

No existen rutas para modificar ni borrar respuestas o ajustes, y la base de
datos lo impide (migraciones 0008 y 0009).
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.en_vivo import adaptador_en_vivo
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
)
from app.adapters.outbound.persistence.repositorio_respuestas import (
    SqlRespuestaRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.respuestas import (
    PuntajesSesion,
    RespuestaNoEncontrada,
    RespuestaRegistrada,
    ServicioRegistroRespuestas,
)
from app.application.sesiones import SesionNoEncontrada
from app.domain.evaluacion import Acumulado
from app.domain.sesiones import ReglaSesionError, TipoTarea
from app.domain.usuarios import PermisoCodigo

router = APIRouter(prefix="/api/sesiones", tags=["respuestas"])


def get_servicio_registro(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioRegistroRespuestas:
    return ServicioRegistroRespuestas(
        SqlSesionRepository(session),
        SqlRespuestaRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
        adaptador_en_vivo(),
    )


Servicio = Annotated[ServicioRegistroRespuestas, Depends(get_servicio_registro)]
Conductor = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_CONDUCIR))
]


class AjusteSalida(BaseModel):
    id: UUID
    puntaje_anterior: float
    puntaje_nuevo: float
    motivo: str
    creado_en: datetime


class RespuestaRegistradaSalida(BaseModel):
    id: UUID
    recibida_en: datetime
    segundos_usados: int
    participante_id: UUID
    participante_nombre: str
    participante_correo: str
    rol_codigo: str
    rol_nombre: str
    inject_orden: int
    inject_titulo: str
    tarea_id: UUID
    tarea_enunciado: str
    tipo: TipoTarea
    tiempo_limite_segundos: int
    texto: str | None
    opciones_elegidas: list[int]
    opciones_elegidas_texto: list[str]
    # Evaluación (PB-10): el puntaje vigente es el del último ajuste, si lo hay.
    puntaje: float
    puntaje_automatico: float
    puntaje_maximo: int
    completitud: float
    precision: float
    tiempo: float
    aciertos: list[str]
    faltantes: list[str]
    errores: list[str]
    ajustes: list[AjusteSalida]

    @classmethod
    def desde(cls, r: RespuestaRegistrada) -> "RespuestaRegistradaSalida":
        return cls(
            id=r.respuesta.id,
            recibida_en=r.respuesta.recibida_en,
            segundos_usados=r.respuesta.segundos_usados,
            participante_id=r.respuesta.usuario_id,
            participante_nombre=r.participante_nombre,
            participante_correo=r.participante_correo,
            rol_codigo=r.respuesta.rol_codigo,
            rol_nombre=r.rol_nombre,
            inject_orden=r.inject_orden,
            inject_titulo=r.inject_titulo,
            tarea_id=r.tarea.id,
            tarea_enunciado=r.tarea.enunciado,
            tipo=r.tarea.tipo,
            tiempo_limite_segundos=r.tarea.tiempo_limite_segundos,
            texto=r.respuesta.texto,
            opciones_elegidas=r.respuesta.opciones_elegidas,
            opciones_elegidas_texto=r.opciones_elegidas_texto,
            puntaje=r.puntaje,
            puntaje_automatico=r.evaluacion.puntaje,
            puntaje_maximo=r.tarea.puntaje_maximo,
            completitud=r.evaluacion.completitud,
            precision=r.evaluacion.precision,
            tiempo=r.evaluacion.tiempo,
            aciertos=r.evaluacion.aciertos,
            faltantes=r.evaluacion.faltantes,
            errores=r.evaluacion.errores,
            ajustes=[
                AjusteSalida(
                    id=a.id,
                    puntaje_anterior=a.puntaje_anterior,
                    puntaje_nuevo=a.puntaje_nuevo,
                    motivo=a.motivo,
                    creado_en=a.creado_en,
                )
                for a in r.ajustes
            ],
        )


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada") from None
    except RespuestaNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Respuesta no encontrada"
        ) from None
    except ReglaSesionError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e


@router.get("/{sesion_id}/respuestas", response_model=list[RespuestaRegistradaSalida])
def respuestas_de_la_sesion(sesion_id: UUID, servicio: Servicio, usuario: Conductor):
    """Todas las respuestas de la sesión, en orden de llegada."""
    registro = _manejar_errores(lambda: servicio.de_sesion(sesion_id, usuario.id))
    return [RespuestaRegistradaSalida.desde(r) for r in registro]


class AjusteEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    puntaje: float = Field(allow_inf_nan=False)
    motivo: str = Field(max_length=1000)


@router.post(
    "/{sesion_id}/respuestas/{respuesta_id}/ajustes",
    response_model=RespuestaRegistradaSalida,
    status_code=status.HTTP_201_CREATED,
)
def ajustar_puntaje(
    sesion_id: UUID,
    respuesta_id: UUID,
    datos: AjusteEntrada,
    servicio: Servicio,
    usuario: Conductor,
):
    """Ajuste manual: entre 0 y el máximo de la tarea, con motivo (422 si no)."""
    registrada = _manejar_errores(
        lambda: servicio.ajustar(
            sesion_id, usuario.id, respuesta_id, datos.puntaje, datos.motivo
        )
    )
    return RespuestaRegistradaSalida.desde(registrada)


class AcumuladoSalida(BaseModel):
    puntaje: float
    maximo: int
    porcentaje: float
    respondidas: int
    sin_responder: int

    @classmethod
    def desde(cls, a: Acumulado) -> "AcumuladoSalida":
        return cls(
            puntaje=a.puntaje,
            maximo=a.maximo,
            porcentaje=a.porcentaje,
            respondidas=a.respondidas,
            sin_responder=a.sin_responder,
        )


class PuntajeParticipanteSalida(AcumuladoSalida):
    usuario_id: UUID
    nombre: str
    rol_codigo: str
    rol_nombre: str


class PuntajeRolSalida(AcumuladoSalida):
    rol_codigo: str
    rol_nombre: str
    participantes: int


class PuntajesSalida(BaseModel):
    participantes: list[PuntajeParticipanteSalida]
    roles: list[PuntajeRolSalida]

    @classmethod
    def desde(cls, p: PuntajesSesion) -> "PuntajesSalida":
        return cls(
            participantes=[
                PuntajeParticipanteSalida(
                    **AcumuladoSalida.desde(x.acumulado).model_dump(),
                    usuario_id=x.usuario_id,
                    nombre=x.nombre,
                    rol_codigo=x.rol_codigo,
                    rol_nombre=x.rol_nombre,
                )
                for x in p.participantes
            ],
            roles=[
                PuntajeRolSalida(
                    **AcumuladoSalida.desde(x.acumulado).model_dump(),
                    rol_codigo=x.rol_codigo,
                    rol_nombre=x.rol_nombre,
                    participantes=x.participantes,
                )
                for x in p.roles
            ],
        )


@router.get("/{sesion_id}/puntajes", response_model=PuntajesSalida)
def puntajes_de_la_sesion(sesion_id: UUID, servicio: Servicio, usuario: Conductor):
    """Acumulado sobre las tareas de los injects lanzados (sin responder = 0)."""
    puntajes = _manejar_errores(lambda: servicio.puntajes(sesion_id, usuario.id))
    return PuntajesSalida.desde(puntajes)
