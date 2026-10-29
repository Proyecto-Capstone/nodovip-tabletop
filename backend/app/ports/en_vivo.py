"""Puertos del motor en tiempo real (PB-07).

`AlmacenEnVivo` guarda el estado activo de cada sesión, cuenta las conexiones
y publica eventos; lo usan los comandos REST (código síncrono).
`SuscriptorEnVivo` entrega esos eventos a cada WebSocket (código asíncrono).
"""

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo


class AlmacenEnVivo(Protocol):
    def obtener(self, sesion_id: UUID) -> EstadoEnVivo | None: ...

    def guardar(self, estado: EstadoEnVivo) -> None: ...

    def eliminar(self, sesion_id: UUID) -> None: ...

    def publicar(self, evento: EventoEnVivo) -> None:
        """Avisa a todas las conexiones de la sesión (en cualquier proceso)."""
        ...

    def conectar(self, sesion_id: UUID, usuario_id: UUID) -> None: ...

    def desconectar(self, sesion_id: UUID, usuario_id: UUID) -> None: ...

    def conectados(self, sesion_id: UUID) -> frozenset[UUID]: ...


class SuscriptorEnVivo(Protocol):
    def escuchar(self, sesion_id: UUID) -> AsyncIterator[EventoEnVivo]:
        """Eventos publicados para la sesión, a medida que llegan.

        El primero es siempre `suscrito`, emitido cuando la suscripción ya está
        activa."""
        ...
