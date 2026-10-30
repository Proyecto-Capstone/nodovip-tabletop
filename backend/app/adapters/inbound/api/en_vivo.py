"""Conducción de la sesión en tiempo real (PB-07, RF-02).

- Comandos del moderador por REST: iniciar, lanzar inject, pausar, reanudar y
  cerrar (permiso `sesiones:conducir`, solo sobre sus sesiones).
- `ws /api/ws/sesiones/{id}`: el moderador y los participantes invitados
  reciben el estado en vivo. Es de solo recepción: el participante no puede
  cambiar el estado de la sesión.

Mensajes: `{"tipo": "estado", "vista": ...}` para todos y, solo al moderador,
`{"tipo": "respuesta"}` cuando llega una respuesta (PB-11: el panel recarga el
avance y los puntajes).

Códigos de cierre del WebSocket: 4401 sin sesión iniciada, 4403 rol sin
permiso, 4404 sesión inexistente o sin invitación, 1000 la sesión terminó.
"""

from collections.abc import Iterator
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
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.application.en_vivo import ServicioEnVivo, VistaEnVivo, componer_vista
from app.application.sesiones import SesionNoEncontrada
from app.domain.sesiones import EstadoSesion, ReglaSesionError
from app.domain.usuarios import PermisoCodigo
from app.ports.en_vivo import SuscriptorEnVivo

router = APIRouter(tags=["en vivo"])


def get_servicio_en_vivo(
    session: Annotated[Session, Depends(get_session)],
) -> Iterator[ServicioEnVivo]:
    yield ServicioEnVivo(SqlSesionRepository(session), adaptador_en_vivo())


def get_suscriptor() -> SuscriptorEnVivo:
    return adaptador_en_vivo()


Servicio = Annotated[ServicioEnVivo, Depends(get_servicio_en_vivo)]
Conductor = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_CONDUCIR))
]


class InjectEnVivo(BaseModel):
    orden: int
    titulo: str
    descripcion: str


class VistaEnVivoSalida(BaseModel):
    sesion_id: UUID
    nombre: str
    estado: EstadoSesion
    total_injects: int
    inject_actual: int
    inject: InjectEnVivo | None
    pausada: bool
    iniciada_en: datetime | None
    inject_lanzado_en: datetime | None
    segundos_transcurridos: int
    duracion_minutos: int | None
    version: int
    total_conectados: int
    # Solo para el moderador: quiénes están conectados.
    conectados: list[UUID] | None = None

    @classmethod
    def desde(cls, v: VistaEnVivo, es_moderador: bool) -> "VistaEnVivoSalida":
        return cls(
            sesion_id=v.sesion_id,
            nombre=v.nombre,
            estado=v.estado,
            total_injects=v.total_injects,
            inject_actual=v.inject_actual,
            inject=InjectEnVivo(
                orden=v.inject.orden,
                titulo=v.inject.titulo,
                descripcion=v.inject.descripcion,
            )
            if v.inject
            else None,
            pausada=v.pausada,
            iniciada_en=v.iniciada_en,
            inject_lanzado_en=v.inject_lanzado_en,
            segundos_transcurridos=v.segundos_transcurridos,
            duracion_minutos=v.duracion_minutos,
            version=v.version,
            total_conectados=len(v.conectados),
            conectados=sorted(v.conectados, key=str) if es_moderador else None,
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


# --- Comandos del moderador (REST) ----------------------------------------------------

BASE = "/api/sesiones/{sesion_id}/en-vivo"


@router.get(BASE, response_model=VistaEnVivoSalida)
def ver_en_vivo(sesion_id: UUID, servicio: Servicio, usuario: Conductor):
    def ver():
        sesion = servicio.sesion_para(sesion_id, usuario.id, es_moderador=True)
        return servicio.vista(sesion)

    return VistaEnVivoSalida.desde(_manejar_errores(ver), es_moderador=True)


def _comando(nombre: str, doc: str):
    def endpoint(sesion_id: UUID, servicio: Servicio, usuario: Conductor):
        metodo = getattr(servicio, nombre)
        vista = _manejar_errores(lambda: metodo(sesion_id, usuario.id))
        return VistaEnVivoSalida.desde(vista, es_moderador=True)

    endpoint.__doc__ = doc
    endpoint.__name__ = f"en_vivo_{nombre}"
    return endpoint


for ruta, nombre, doc in [
    ("iniciar", "iniciar", "Inicia una sesión programada: pasa a en curso."),
    (
        "lanzar-inject",
        "lanzar_inject",
        "Lanza el siguiente inject a todos los conectados.",
    ),
    ("pausar", "pausar", "Pausa la sesión (el tiempo deja de correr)."),
    ("reanudar", "reanudar", "Reanuda una sesión en pausa."),
    ("cerrar", "cerrar", "Cierra la sesión y la persiste en PostgreSQL."),
]:
    router.post(f"{BASE}/{ruta}", response_model=VistaEnVivoSalida)(
        _comando(nombre, doc)
    )


# --- WebSocket ------------------------------------------------------------------------


@router.websocket("/api/ws/sesiones/{sesion_id}")
async def ws_sesion(
    websocket: WebSocket,
    sesion_id: UUID,
    servicio: Annotated[ServicioEnVivo, Depends(get_servicio_en_vivo)],
    suscriptor: Annotated[SuscriptorEnVivo, Depends(get_suscriptor)],
    usuario: Annotated[UsuarioActual | None, Depends(obtener_usuario_ws)],
):
    await websocket.accept()
    if usuario is None:
        await websocket.close(code=4401, reason="No autenticado")
        return
    es_moderador = usuario.puede(PermisoCodigo.SESIONES_CONDUCIR)
    if not es_moderador and not usuario.puede(PermisoCodigo.SESIONES_PARTICIPAR):
        await websocket.close(code=4403, reason="Sin permiso")
        return
    try:
        sesion = await run_in_threadpool(
            servicio.sesion_para, sesion_id, usuario.id, es_moderador
        )
    except SesionNoEncontrada:
        await websocket.close(code=4404, reason="Sesión no encontrada")
        return
    finally:
        # El WebSocket puede durar horas: no retiene la conexión a PostgreSQL.
        liberar = getattr(servicio.sesiones, "liberar", None)
        if liberar:
            liberar()

    async def enviar(vista: VistaEnVivo) -> None:
        salida = VistaEnVivoSalida.desde(vista, es_moderador)
        await websocket.send_json(
            {"tipo": "estado", "vista": salida.model_dump(mode="json")}
        )

    async def reenviar_eventos(grupo: anyio.abc.TaskGroup) -> None:
        estado = None
        conectados = frozenset()
        async for evento in suscriptor.escuchar(sesion_id):
            if evento.tipo == "respuesta":
                # Solo el moderador: el participante no sabe cuándo responden otros.
                if es_moderador:
                    await websocket.send_json({"tipo": "respuesta"})
                continue
            if evento.tipo == "suscrito":
                # Foto inicial: recién ahora, para no perder eventos intermedios.
                vista = await run_in_threadpool(servicio.vista, sesion)
                conectados = vista.conectados
                estado = await run_in_threadpool(servicio.almacen.obtener, sesion_id)
            elif evento.tipo == "estado":
                estado, conectados = evento.estado, evento.conectados
                vista = componer_vista(sesion, estado, conectados, servicio.reloj())
            else:  # presencia
                conectados = evento.conectados
                vista = componer_vista(sesion, estado, conectados, servicio.reloj())
            await enviar(vista)
            if vista.estado == EstadoSesion.FINALIZADA:
                await websocket.close(code=1000)
                break
        grupo.cancel_scope.cancel()

    await run_in_threadpool(servicio.conectar, sesion_id, usuario.id)
    try:
        # Una tarea reenvía los eventos; esta espera a que el cliente se vaya.
        async with anyio.create_task_group() as grupo:
            grupo.start_soon(reenviar_eventos, grupo)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                grupo.cancel_scope.cancel()
    finally:
        # Protegido: debe ejecutarse aunque el servidor cancele la conexión.
        with anyio.CancelScope(shield=True):
            await run_in_threadpool(servicio.desconectar, sesion_id, usuario.id)
