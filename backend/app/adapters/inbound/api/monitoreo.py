"""Monitoreo de sesiones activas para el Administrador (PC-24, RNF).

- `GET /api/monitoreo/sesiones`: cupo y una fila por cada sesión EN_CURSO.
- `GET /api/monitoreo/sesiones/{id}`: detalle de una, con avance por
  participante y rol (nunca texto de respuestas, opciones ni criterios).
- `ws /api/ws/monitoreo/{id}`: el mismo detalle, actualizado en tiempo
  real, igual que `ws_leaderboard` (abre y cierra su propia sesión de BD
  en cada cálculo).

Solo el permiso `sesiones:monitorear` (hoy, únicamente Administrador) deja
pasar; eso resuelve el 401/403. Esta conexión es de solo lectura: a
propósito nunca llama a `ServicioEnVivo.conectar`, para que el
Administrador que entra en modo lectura NO aparezca en la lista de
conectados ni en el contador que ven los participantes (RNF).

Códigos de cierre del WebSocket: 4401 sin sesión iniciada, 4403 sin
permiso, 4404 la sesión no existe o ya no está en curso (se cerró):
monitoreo solo tiene sentido mientras corre. Una sesión en pausa sigue
EN_CURSO (la pausa es solo del estado en vivo, no de PostgreSQL) y por
eso no cierra el socket.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app import config
from app.adapters.inbound.api._websocket_apoyo import enviar_agrupado_por_segundo
from app.adapters.inbound.api.seguridad import (
    UsuarioActual,
    obtener_usuario_ws,
    requiere_permiso,
)
from app.adapters.outbound.en_vivo import adaptador_en_vivo
from app.adapters.outbound.persistence.database import abrir_sesion, get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_respuestas import (
    SqlRespuestaRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.monitoreo import (
    DetalleMonitoreo,
    FilaMonitoreo,
    ResumenMonitoreo,
    ServicioMonitoreo,
)
from app.application.respuestas import PuntajeParticipante, PuntajeRol
from app.application.sesiones import SesionNoEncontrada
from app.domain.usuarios import PermisoCodigo
from app.ports.en_vivo import SuscriptorEnVivo

router = APIRouter(tags=["monitoreo"])


def get_servicio_monitoreo(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioMonitoreo:
    return ServicioMonitoreo(
        SqlSesionRepository(session),
        SqlRespuestaRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
        SqlEscenarioRepository(session),
        adaptador_en_vivo(),
        maximo_activas=config.max_sesiones_activas(),
    )


def get_suscriptor() -> SuscriptorEnVivo:
    return adaptador_en_vivo()


Servicio = Annotated[ServicioMonitoreo, Depends(get_servicio_monitoreo)]
ConPermiso = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_MONITOREAR))
]


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada") from None


# --- Esquemas de salida -----------------------------------------------------------------


class FilaMonitoreoSalida(BaseModel):
    id: UUID
    nombre: str
    moderador_nombre: str
    escenario_nombre: str
    pausada: bool
    invitados: int
    conectados: int
    inject_actual: int
    total_injects: int
    respuestas_recibidas: int
    respuestas_esperadas: int
    porcentaje_avance: float
    segundos_transcurridos: int
    iniciada_en: datetime | None
    duracion_minutos: int | None
    excede_duracion: bool

    @classmethod
    def desde(cls, f: FilaMonitoreo) -> "FilaMonitoreoSalida":
        return cls(
            id=f.id,
            nombre=f.nombre,
            moderador_nombre=f.moderador_nombre,
            escenario_nombre=f.escenario_nombre,
            pausada=f.pausada,
            invitados=f.invitados,
            conectados=f.conectados,
            inject_actual=f.inject_actual,
            total_injects=f.total_injects,
            respuestas_recibidas=f.respuestas_recibidas,
            respuestas_esperadas=f.respuestas_esperadas,
            porcentaje_avance=f.porcentaje_avance,
            segundos_transcurridos=f.segundos_transcurridos,
            iniciada_en=f.iniciada_en,
            duracion_minutos=f.duracion_minutos,
            excede_duracion=f.excede_duracion,
        )


class ResumenMonitoreoSalida(BaseModel):
    activas: int
    maximo: int
    sesiones: list[FilaMonitoreoSalida]

    @classmethod
    def desde(cls, r: ResumenMonitoreo) -> "ResumenMonitoreoSalida":
        return cls(
            activas=r.activas,
            maximo=r.maximo,
            sesiones=[FilaMonitoreoSalida.desde(f) for f in r.sesiones],
        )


class PuntajeParticipanteSalida(BaseModel):
    """Nunca lleva texto de respuestas, opciones ni criterios: solo el acumulado."""

    usuario_id: UUID
    nombre: str
    rol_codigo: str
    rol_nombre: str
    puntaje: float
    maximo: int
    porcentaje: float
    respondidas: int
    sin_responder: int

    @classmethod
    def desde(cls, p: PuntajeParticipante) -> "PuntajeParticipanteSalida":
        return cls(
            usuario_id=p.usuario_id,
            nombre=p.nombre,
            rol_codigo=p.rol_codigo,
            rol_nombre=p.rol_nombre,
            puntaje=p.acumulado.puntaje,
            maximo=p.acumulado.maximo,
            porcentaje=p.acumulado.porcentaje,
            respondidas=p.acumulado.respondidas,
            sin_responder=p.acumulado.sin_responder,
        )


class PuntajeRolSalida(BaseModel):
    rol_codigo: str
    rol_nombre: str
    participantes: int
    puntaje: float
    maximo: int
    porcentaje: float
    respondidas: int
    sin_responder: int

    @classmethod
    def desde(cls, r: PuntajeRol) -> "PuntajeRolSalida":
        return cls(
            rol_codigo=r.rol_codigo,
            rol_nombre=r.rol_nombre,
            participantes=r.participantes,
            puntaje=r.acumulado.puntaje,
            maximo=r.acumulado.maximo,
            porcentaje=r.acumulado.porcentaje,
            respondidas=r.acumulado.respondidas,
            sin_responder=r.acumulado.sin_responder,
        )


class DetalleMonitoreoSalida(BaseModel):
    sesion: FilaMonitoreoSalida
    participantes: list[PuntajeParticipanteSalida]
    roles: list[PuntajeRolSalida]

    @classmethod
    def desde(cls, d: DetalleMonitoreo) -> "DetalleMonitoreoSalida":
        return cls(
            sesion=FilaMonitoreoSalida.desde(d.sesion),
            participantes=[PuntajeParticipanteSalida.desde(p) for p in d.participantes],
            roles=[PuntajeRolSalida.desde(r) for r in d.roles],
        )


# --- REST --------------------------------------------------------------------------------


@router.get("/api/monitoreo/sesiones", response_model=ResumenMonitoreoSalida)
def sesiones_activas(servicio: Servicio, _usuario: ConPermiso):
    """Cupo y una fila por cada sesión EN_CURSO (PC-24)."""
    return ResumenMonitoreoSalida.desde(servicio.resumen())


@router.get(
    "/api/monitoreo/sesiones/{sesion_id}", response_model=DetalleMonitoreoSalida
)
def detalle_de_la_sesion(sesion_id: UUID, servicio: Servicio, _usuario: ConPermiso):
    """Detalle de una sesión EN_CURSO. 404 si no existe o ya no está en curso."""
    detalle = _manejar_errores(lambda: servicio.detalle(sesion_id))
    return DetalleMonitoreoSalida.desde(detalle)


# --- WebSocket -----------------------------------------------------------------------------

# Igual que el leaderboard: "presencia" se ignora porque no cambia el
# avance a mostrar; cualquier otro tipo futuro también se ignora.
EVENTOS_RELEVANTES = frozenset({"suscrito", "respuesta", "ajuste", "estado"})


CalculadorDetalle = Callable[[UUID], DetalleMonitoreo]


def calculador_detalle() -> CalculadorDetalle:
    """Como `calculador_ranking` del leaderboard: abre y cierra su propia
    sesión de BD en cada llamada, porque el WebSocket puede durar horas."""

    def calcular(sesion_id: UUID) -> DetalleMonitoreo:
        with abrir_sesion() as session:
            servicio = ServicioMonitoreo(
                SqlSesionRepository(session),
                SqlRespuestaRepository(session),
                SqlCatalogoRepository(session),
                SqlUsuarioRepository(session),
                SqlEscenarioRepository(session),
                adaptador_en_vivo(),
                maximo_activas=config.max_sesiones_activas(),
            )
            return servicio.detalle(sesion_id)

    return calcular


@router.websocket("/api/ws/monitoreo/{sesion_id}")
async def ws_monitoreo(
    websocket: WebSocket,
    sesion_id: UUID,
    suscriptor: Annotated[SuscriptorEnVivo, Depends(get_suscriptor)],
    usuario: Annotated[UsuarioActual | None, Depends(obtener_usuario_ws)],
    calcular: Annotated[CalculadorDetalle, Depends(calculador_detalle)],
):
    await websocket.accept()
    if usuario is None:
        await websocket.close(code=4401, reason="No autenticado")
        return
    if not usuario.puede(PermisoCodigo.SESIONES_MONITOREAR):
        await websocket.close(code=4403, reason="Sin permiso")
        return

    # A propósito no se llama a almacen.conectar(): quien mira en modo
    # lectura no debe aparecer como "conectado" para los participantes.
    async def enviar() -> bool:
        """Calcula y envía el detalle más reciente. True si ya cerró el socket."""
        try:
            detalle = await run_in_threadpool(calcular, sesion_id)
        except SesionNoEncontrada:
            # Incluye "ya no está en curso" (se cerró, o nunca existió):
            # ServicioMonitoreo.detalle no distingue uno de otro.
            await websocket.close(
                code=4404, reason="Sesión no encontrada o ya no está en curso"
            )
            return True
        salida = DetalleMonitoreoSalida.desde(detalle)
        await websocket.send_json(
            {"tipo": "monitoreo", "datos": salida.model_dump(mode="json")}
        )
        return False

    async with anyio.create_task_group() as grupo:
        await enviar_agrupado_por_segundo(
            grupo, suscriptor.escuchar(sesion_id), EVENTOS_RELEVANTES, enviar
        )
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            grupo.cancel_scope.cancel()
