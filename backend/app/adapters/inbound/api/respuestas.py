"""Registro trazable de respuestas de una sesión (PB-09, RF-07).

`GET /api/sesiones/{id}/respuestas`: solo lectura, para el moderador dueño de
la sesión (permiso `sesiones:conducir`). Lo usarán el panel del moderador
(PB-11) y el reporte (PB-14). No existen rutas para modificar ni borrar
respuestas, y la base de datos lo impide (migración 0008).
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
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
from app.application.respuestas import RespuestaRegistrada, ServicioRegistroRespuestas
from app.application.sesiones import SesionNoEncontrada
from app.domain.sesiones import TipoTarea
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
    )


Servicio = Annotated[ServicioRegistroRespuestas, Depends(get_servicio_registro)]
Conductor = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_CONDUCIR))
]


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
        )


@router.get("/{sesion_id}/respuestas", response_model=list[RespuestaRegistradaSalida])
def respuestas_de_la_sesion(sesion_id: UUID, servicio: Servicio, usuario: Conductor):
    """Todas las respuestas de la sesión, en orden de llegada."""
    try:
        registro = servicio.de_sesion(sesion_id, usuario.id)
    except SesionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada") from None
    return [RespuestaRegistradaSalida.desde(r) for r in registro]
