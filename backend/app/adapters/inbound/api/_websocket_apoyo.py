"""Apoyo compartido para WebSocket de solo recepción con eventos agrupados.

Extraído de `ws_leaderboard` (PB-12) para que `ws_monitoreo` (PC-24) no
duplique la misma lógica: como máximo un envío por segundo por conexión, con
el estado más reciente — si llegan varios eventos relevantes casi juntos, se
calcula una sola vez, nunca una vez por cada evento.
"""

from collections.abc import AsyncIterator, Awaitable, Callable

import anyio
import anyio.abc

from app.domain.en_vivo import EventoEnVivo

INTERVALO_MINIMO_SEGUNDOS = 1.0


async def enviar_agrupado_por_segundo(
    grupo: anyio.abc.TaskGroup,
    eventos: AsyncIterator[EventoEnVivo],
    eventos_relevantes: frozenset[str],
    enviar: Callable[[], Awaitable[bool]],
    intervalo_minimo_segundos: float = INTERVALO_MINIMO_SEGUNDOS,
) -> None:
    """Arranca, dentro de `grupo`, las dos tareas que agrupan ráfagas de
    eventos en un envío por segundo como máximo.

    `enviar` calcula y manda el mensaje más reciente; debe devolver `True`
    si ya cerró el socket (con eso termina el grupo). El límite solo puede
    *agregar* hasta `intervalo_minimo_segundos` de espera dentro de una
    ráfaga, nunca más — sigue cumpliendo un requisito de latencia ≤ 3 s.
    """
    cambio = anyio.Event()

    async def marcar_cambios() -> None:
        nonlocal cambio
        async for evento in eventos:
            if evento.tipo in eventos_relevantes:
                cambio.set()
        grupo.cancel_scope.cancel()

    async def enviar_cuando_cambie() -> None:
        nonlocal cambio
        ultimo_envio: float | None = None
        while True:
            await cambio.wait()
            # Se reemplaza antes de calcular: lo que llegue durante el
            # cálculo o la espera se junta en el próximo envío, no se pierde.
            cambio = anyio.Event()
            if ultimo_envio is not None:
                falta = intervalo_minimo_segundos - (
                    anyio.current_time() - ultimo_envio
                )
                if falta > 0:
                    await anyio.sleep(falta)
            terminado = await enviar()
            ultimo_envio = anyio.current_time()
            if terminado:
                grupo.cancel_scope.cancel()
                return

    grupo.start_soon(marcar_cambios)
    grupo.start_soon(enviar_cuando_cambie)
