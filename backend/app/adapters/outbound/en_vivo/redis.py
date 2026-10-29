"""Estado en vivo en Redis (PB-07).

Claves por sesión, para aislar las sesiones simultáneas (RNF-04):
- `nodovip:sesion:{id}:estado`     JSON del EstadoEnVivo (expira a las 24 h)
- `nodovip:sesion:{id}:conectados` hash usuario → conexiones abiertas
- `nodovip:sesion:{id}:eventos`    canal pub/sub hacia los WebSocket

PostgreSQL sigue siendo la fuente de verdad: si Redis se pierde, el servicio
reconstruye el estado desde la sesión guardada.
"""

import json
from collections.abc import AsyncIterator
from uuid import UUID

import redis
import redis.asyncio as redis_async

from app.adapters.outbound.en_vivo.serializacion import (
    estado_a_dict,
    estado_desde_dict,
    evento_a_dict,
    evento_desde_dict,
)
from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo

EXPIRACION_SEGUNDOS = 24 * 3600


def _clave(sesion_id: UUID, parte: str) -> str:
    return f"nodovip:sesion:{sesion_id}:{parte}"


class EnVivoRedis:
    def __init__(self, url: str):
        self._url = url
        self._r = redis.Redis.from_url(url, decode_responses=True)

    # --- AlmacenEnVivo --------------------------------------------------------

    def obtener(self, sesion_id: UUID) -> EstadoEnVivo | None:
        datos = self._r.get(_clave(sesion_id, "estado"))
        return estado_desde_dict(json.loads(datos)) if datos else None

    def guardar(self, estado: EstadoEnVivo) -> None:
        self._r.set(
            _clave(estado.sesion_id, "estado"),
            json.dumps(estado_a_dict(estado)),
            ex=EXPIRACION_SEGUNDOS,
        )

    def eliminar(self, sesion_id: UUID) -> None:
        self._r.delete(_clave(sesion_id, "estado"), _clave(sesion_id, "conectados"))

    def publicar(self, evento: EventoEnVivo) -> None:
        self._r.publish(
            _clave(evento.sesion_id, "eventos"), json.dumps(evento_a_dict(evento))
        )

    def conectar(self, sesion_id: UUID, usuario_id: UUID) -> None:
        clave = _clave(sesion_id, "conectados")
        self._r.hincrby(clave, str(usuario_id), 1)
        self._r.expire(clave, EXPIRACION_SEGUNDOS)

    def desconectar(self, sesion_id: UUID, usuario_id: UUID) -> None:
        clave = _clave(sesion_id, "conectados")
        if self._r.hincrby(clave, str(usuario_id), -1) <= 0:
            self._r.hdel(clave, str(usuario_id))

    def conectados(self, sesion_id: UUID) -> frozenset[UUID]:
        return frozenset(
            UUID(u) for u in self._r.hkeys(_clave(sesion_id, "conectados"))
        )

    # --- SuscriptorEnVivo -----------------------------------------------------

    async def escuchar(self, sesion_id: UUID) -> AsyncIterator[EventoEnVivo]:
        cliente = redis_async.Redis.from_url(self._url, decode_responses=True)
        canal = cliente.pubsub()
        await canal.subscribe(_clave(sesion_id, "eventos"))
        try:
            yield EventoEnVivo(sesion_id, "suscrito")
            async for mensaje in canal.listen():
                if mensaje["type"] == "message":
                    yield evento_desde_dict(json.loads(mensaje["data"]))
        finally:
            await canal.unsubscribe()
            await canal.aclose()
            await cliente.aclose()
