"""Estado en vivo en memoria: para pruebas y para correr sin Redis en local.

Solo sirve con un único proceso. Los comandos REST corren en hilos del
threadpool y los WebSocket en el event loop: los eventos se entregan con
`call_soon_threadsafe` para cruzar de un lado al otro sin carreras.
"""

import asyncio
import copy
import threading
from collections import defaultdict
from collections.abc import AsyncIterator
from uuid import UUID

from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo


class EnVivoEnMemoria:
    def __init__(self):
        self._estados: dict[UUID, EstadoEnVivo] = {}
        self._conexiones: dict[UUID, dict[UUID, int]] = defaultdict(dict)
        self._suscriptores: dict[
            UUID, list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]
        ] = defaultdict(list)
        self._candado = threading.Lock()

    # --- AlmacenEnVivo --------------------------------------------------------

    def obtener(self, sesion_id: UUID) -> EstadoEnVivo | None:
        with self._candado:
            e = self._estados.get(sesion_id)
            return copy.deepcopy(e) if e else None

    def guardar(self, estado: EstadoEnVivo) -> None:
        with self._candado:
            self._estados[estado.sesion_id] = copy.deepcopy(estado)

    def eliminar(self, sesion_id: UUID) -> None:
        with self._candado:
            self._estados.pop(sesion_id, None)
            self._conexiones.pop(sesion_id, None)

    def publicar(self, evento: EventoEnVivo) -> None:
        with self._candado:
            destinos = list(self._suscriptores.get(evento.sesion_id, []))
        for loop, cola in destinos:
            loop.call_soon_threadsafe(cola.put_nowait, copy.deepcopy(evento))

    def conectar(self, sesion_id: UUID, usuario_id: UUID) -> None:
        with self._candado:
            cuenta = self._conexiones[sesion_id]
            cuenta[usuario_id] = cuenta.get(usuario_id, 0) + 1

    def desconectar(self, sesion_id: UUID, usuario_id: UUID) -> None:
        with self._candado:
            cuenta = self._conexiones[sesion_id]
            restantes = cuenta.get(usuario_id, 0) - 1
            if restantes > 0:
                cuenta[usuario_id] = restantes
            else:
                cuenta.pop(usuario_id, None)

    def conectados(self, sesion_id: UUID) -> frozenset[UUID]:
        with self._candado:
            return frozenset(self._conexiones.get(sesion_id, {}))

    # --- SuscriptorEnVivo -----------------------------------------------------

    async def escuchar(self, sesion_id: UUID) -> AsyncIterator[EventoEnVivo]:
        cola: asyncio.Queue = asyncio.Queue()
        entrada = (asyncio.get_running_loop(), cola)
        with self._candado:
            self._suscriptores[sesion_id].append(entrada)
        try:
            yield EventoEnVivo(sesion_id, "suscrito")
            while True:
                yield await cola.get()
        finally:
            with self._candado:
                self._suscriptores[sesion_id].remove(entrada)
