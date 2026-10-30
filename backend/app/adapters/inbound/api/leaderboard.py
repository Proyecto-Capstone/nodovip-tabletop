"""Leaderboard en vivo para observadores (PB-12, RF-02).

- `GET /api/leaderboard/sesiones`: sesiones en curso o finalizadas visibles
  para el usuario (permiso `leaderboard:ver`).
- `GET /api/leaderboard/sesiones/{id}`: ranking por participante y por rol.
- `ws /api/ws/leaderboard/{id}`: el mismo ranking, actualizado en tiempo
  real. Es de solo recepción y no retiene una conexión de PostgreSQL entre
  envíos (abre y cierra su propia sesión de BD en cada cálculo, igual que
  `obtener_usuario_ws`).

El permiso `leaderboard:ver` ya resuelve el 401/403 (sin sesión o sin
permiso). Dentro, el Moderador solo ve sus propias sesiones; Observador y
Administrador ven cualquiera en curso o finalizada (`ServicioLeaderboard`).

Códigos de cierre del WebSocket: 4401 sin sesión iniciada, 4403 sin
permiso, 4404 sesión no visible, 1000 la sesión terminó (después de enviar
el ranking final).
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

import anyio
import anyio.abc
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.adapters.inbound.api.seguridad import (
    UsuarioActual,
    obtener_usuario_ws,
    requiere_permiso,
)
from app.adapters.outbound.en_vivo import adaptador_en_vivo
from app.adapters.outbound.persistence.database import abrir_sesion, get_session
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
from app.application.leaderboard import (
    PosicionParticipante,
    PosicionRol,
    RankingLeaderboard,
    ServicioLeaderboard,
    SesionLeaderboard,
)
from app.application.sesiones import SesionNoEncontrada
from app.domain.sesiones import EstadoSesion
from app.domain.usuarios import PermisoCodigo
from app.ports.en_vivo import SuscriptorEnVivo

router = APIRouter(tags=["leaderboard"])


def get_servicio_leaderboard(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioLeaderboard:
    return ServicioLeaderboard(
        SqlSesionRepository(session),
        SqlRespuestaRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
        adaptador_en_vivo(),
    )


def get_suscriptor() -> SuscriptorEnVivo:
    return adaptador_en_vivo()


Servicio = Annotated[ServicioLeaderboard, Depends(get_servicio_leaderboard)]
ConPermiso = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.LEADERBOARD_VER))
]


def _es_moderador(usuario: UsuarioActual) -> bool:
    # Mismo criterio que ws_sesion: por permiso, no por el nombre del rol.
    return usuario.puede(PermisoCodigo.SESIONES_CONDUCIR)


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada") from None


# --- Esquemas de salida -----------------------------------------------------------------


class SesionLeaderboardSalida(BaseModel):
    id: UUID
    nombre: str
    estado: EstadoSesion
    total_injects: int
    inject_actual: int
    iniciada_en: datetime | None
    finalizada_en: datetime | None

    @classmethod
    def desde(cls, s: SesionLeaderboard) -> "SesionLeaderboardSalida":
        return cls(
            id=s.id,
            nombre=s.nombre,
            estado=s.estado,
            total_injects=s.total_injects,
            inject_actual=s.inject_actual,
            iniciada_en=s.iniciada_en,
            finalizada_en=s.finalizada_en,
        )


class PosicionParticipanteSalida(BaseModel):
    """Nunca lleva texto de respuestas, opciones ni criterios: solo el acumulado."""

    posicion: int
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
    def desde(cls, p: PosicionParticipante) -> "PosicionParticipanteSalida":
        return cls(
            posicion=p.posicion,
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


class PosicionRolSalida(BaseModel):
    posicion: int
    rol_codigo: str
    rol_nombre: str
    participantes: int
    puntaje: float
    maximo: int
    porcentaje: float
    respondidas: int
    sin_responder: int

    @classmethod
    def desde(cls, r: PosicionRol) -> "PosicionRolSalida":
        return cls(
            posicion=r.posicion,
            rol_codigo=r.rol_codigo,
            rol_nombre=r.rol_nombre,
            participantes=r.participantes,
            puntaje=r.acumulado.puntaje,
            maximo=r.acumulado.maximo,
            porcentaje=r.acumulado.porcentaje,
            respondidas=r.acumulado.respondidas,
            sin_responder=r.acumulado.sin_responder,
        )


class LeaderboardSalida(BaseModel):
    sesion: SesionLeaderboardSalida
    actualizado_en: datetime
    participantes: list[PosicionParticipanteSalida]
    roles: list[PosicionRolSalida]

    @classmethod
    def desde(cls, r: RankingLeaderboard) -> "LeaderboardSalida":
        return cls(
            sesion=SesionLeaderboardSalida.desde(r.sesion),
            actualizado_en=r.actualizado_en,
            participantes=[
                PosicionParticipanteSalida.desde(p) for p in r.participantes
            ],
            roles=[PosicionRolSalida.desde(x) for x in r.roles],
        )


# --- REST --------------------------------------------------------------------------------


@router.get("/api/leaderboard/sesiones", response_model=list[SesionLeaderboardSalida])
def sesiones_del_leaderboard(servicio: Servicio, usuario: ConPermiso):
    """Sesiones en curso o finalizadas que el usuario puede ver (PB-12)."""
    sesiones = servicio.sesiones_visibles(usuario.id, _es_moderador(usuario))
    return [SesionLeaderboardSalida.desde(s) for s in sesiones]


@router.get("/api/leaderboard/sesiones/{sesion_id}", response_model=LeaderboardSalida)
def leaderboard_de_la_sesion(sesion_id: UUID, servicio: Servicio, usuario: ConPermiso):
    """Ranking por participante y por rol. 404 si la sesión no es visible."""
    ranking = _manejar_errores(
        lambda: servicio.ranking(sesion_id, usuario.id, _es_moderador(usuario))
    )
    return LeaderboardSalida.desde(ranking)


# --- WebSocket -----------------------------------------------------------------------------

# Como máximo un recálculo por segundo por conexión: si llegan varios eventos
# juntos, se calcula una sola vez con el estado más reciente (sigue
# cumpliendo el requisito de ≤ 3 s de latencia).
INTERVALO_MINIMO_SEGUNDOS = 1.0

# Eventos que ameritan recalcular el ranking; "presencia" (y cualquier otro
# tipo futuro) se ignora.
EVENTOS_RELEVANTES = frozenset({"suscrito", "respuesta", "ajuste", "estado"})


CalculadorRanking = Callable[[UUID, UUID, bool], RankingLeaderboard]


def calculador_ranking() -> CalculadorRanking:
    """Función que calcula el ranking abriendo y cerrando su propia sesión de
    BD en cada llamada (el WebSocket puede durar horas). Es una dependencia
    para poder reemplazarla por dobles en las pruebas."""

    def calcular(
        sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> RankingLeaderboard:
        with abrir_sesion() as session:
            servicio = ServicioLeaderboard(
                SqlSesionRepository(session),
                SqlRespuestaRepository(session),
                SqlCatalogoRepository(session),
                SqlUsuarioRepository(session),
                adaptador_en_vivo(),
            )
            return servicio.ranking(sesion_id, usuario_id, es_moderador)

    return calcular


@router.websocket("/api/ws/leaderboard/{sesion_id}")
async def ws_leaderboard(
    websocket: WebSocket,
    sesion_id: UUID,
    suscriptor: Annotated[SuscriptorEnVivo, Depends(get_suscriptor)],
    usuario: Annotated[UsuarioActual | None, Depends(obtener_usuario_ws)],
    calcular: Annotated[CalculadorRanking, Depends(calculador_ranking)],
):
    await websocket.accept()
    if usuario is None:
        await websocket.close(code=4401, reason="No autenticado")
        return
    if not usuario.puede(PermisoCodigo.LEADERBOARD_VER):
        await websocket.close(code=4403, reason="Sin permiso")
        return
    es_moderador = _es_moderador(usuario)

    async def enviar() -> bool:
        """Calcula y envía el ranking más reciente. True si ya cerró el socket."""
        try:
            ranking = await run_in_threadpool(
                calcular, sesion_id, usuario.id, es_moderador
            )
        except SesionNoEncontrada:
            await websocket.close(code=4404, reason="Sesión no encontrada")
            return True
        salida = LeaderboardSalida.desde(ranking)
        await websocket.send_json(
            {"tipo": "leaderboard", "datos": salida.model_dump(mode="json")}
        )
        if ranking.sesion.estado == EstadoSesion.FINALIZADA:
            await websocket.close(code=1000)
            return True
        return False

    cambio = anyio.Event()

    async def marcar_cambios(grupo: anyio.abc.TaskGroup) -> None:
        nonlocal cambio
        async for evento in suscriptor.escuchar(sesion_id):
            if evento.tipo in EVENTOS_RELEVANTES:
                cambio.set()
        grupo.cancel_scope.cancel()

    async def enviar_agrupado(grupo: anyio.abc.TaskGroup) -> None:
        nonlocal cambio
        ultimo_envio: float | None = None
        while True:
            await cambio.wait()
            # Se reemplaza antes de calcular: lo que llegue durante el
            # cálculo o la espera se junta en el próximo envío, no se pierde.
            cambio = anyio.Event()
            if ultimo_envio is not None:
                falta = INTERVALO_MINIMO_SEGUNDOS - (
                    anyio.current_time() - ultimo_envio
                )
                if falta > 0:
                    await anyio.sleep(falta)
            terminado = await enviar()
            ultimo_envio = anyio.current_time()
            if terminado:
                grupo.cancel_scope.cancel()
                return

    async with anyio.create_task_group() as grupo:
        grupo.start_soon(marcar_cambios, grupo)
        grupo.start_soon(enviar_agrupado, grupo)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            grupo.cancel_scope.cancel()
