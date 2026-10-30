"""Aislamiento del estado en vivo entre sesiones simultáneas (PC-24, RNF-04).

Corre contra el adaptador en memoria siempre, y contra Redis si existe
TEST_REDIS_URL (en local, con Docker levantado):

    TEST_REDIS_URL=redis://:clave@localhost:6379/1 pytest -q tests/test_aislamiento_en_vivo.py

Usa la base 1 de Redis para no tocar el estado de la aplicación (base 0).
No repite las pruebas de un solo estado/estado de test_en_vivo_redis.py:
aquí el punto es que 10 sesiones a la vez (como las que permite
MAX_SESIONES_ACTIVAS) nunca mezclan su estado, sus conectados ni sus
eventos entre sí, y que borrar una no toca a las demás.
"""

import asyncio
import os
import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.adapters.outbound.en_vivo.redis import EnVivoRedis
from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo

REDIS_URL = os.getenv("TEST_REDIS_URL")
N_SESIONES = 10


@pytest.fixture(
    params=[
        "memoria",
        pytest.param(
            "redis",
            marks=pytest.mark.skipif(
                not REDIS_URL, reason="TEST_REDIS_URL no definido"
            ),
        ),
    ]
)
def almacen(request):
    adaptador = (
        EnVivoEnMemoria() if request.param == "memoria" else EnVivoRedis(REDIS_URL)
    )
    ids = [uuid4() for _ in range(N_SESIONES)]
    yield adaptador, ids
    for sid in ids:
        adaptador.eliminar(sid)


def test_guardar_en_paralelo_no_mezcla_el_estado_entre_sesiones(almacen):
    """10 sesiones "lanzando injects" a la vez: cada una conserva el suyo."""
    adaptador, ids = almacen
    barrera = threading.Barrier(len(ids))

    def lanzar(i: int, sid):
        estado = EstadoEnVivo(
            sid, total_injects=N_SESIONES, iniciada_en=datetime.now(UTC)
        )
        for _ in range(i + 1):
            estado.lanzar_siguiente_inject(datetime.now(UTC))
        barrera.wait()
        adaptador.guardar(estado)

    hilos = [
        threading.Thread(target=lanzar, args=(i, sid)) for i, sid in enumerate(ids)
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    for i, sid in enumerate(ids):
        leido = adaptador.obtener(sid)
        assert leido is not None
        assert leido.sesion_id == sid
        assert leido.inject_actual == i + 1


def test_conectados_es_independiente_por_sesion(almacen):
    adaptador, ids = almacen
    usuarios = [uuid4() for _ in ids]
    for sid, uid in zip(ids, usuarios, strict=True):
        adaptador.conectar(sid, uid)

    for sid, uid in zip(ids, usuarios, strict=True):
        assert adaptador.conectados(sid) == {uid}


def test_eliminar_una_sesion_no_afecta_a_las_demas(almacen):
    adaptador, ids = almacen
    for sid in ids:
        adaptador.guardar(
            EstadoEnVivo(sid, total_injects=1, iniciada_en=datetime.now(UTC))
        )
        adaptador.conectar(sid, uuid4())

    eliminada, resto = ids[0], ids[1:]
    adaptador.eliminar(eliminada)

    assert adaptador.obtener(eliminada) is None
    for sid in resto:
        assert adaptador.obtener(sid) is not None
        assert adaptador.conectados(sid)


def test_ningun_suscriptor_recibe_eventos_de_otra_sesion(almacen):
    """10 sesiones conectadas a la vez por WebSocket (aquí, 10 suscriptores):
    un evento de una sola nunca llega a los demás."""
    adaptador, ids = almacen

    async def escuchar_uno(sid, listo: asyncio.Event):
        eventos = adaptador.escuchar(sid)
        primero = await anext(eventos)
        assert primero.tipo == "suscrito"
        listo.set()
        try:
            recibido = await asyncio.wait_for(anext(eventos), timeout=2)
        except TimeoutError:
            recibido = None
        await eventos.aclose()
        return recibido

    async def correr():
        listos = [asyncio.Event() for _ in ids]
        tareas = [
            asyncio.create_task(escuchar_uno(sid, listo))
            for sid, listo in zip(ids, listos, strict=True)
        ]
        # Recién cuando los 10 ya están suscritos se publica, para que el
        # resultado no dependa de una carrera entre publicar y suscribirse.
        await asyncio.gather(*(listo.wait() for listo in listos))
        adaptador.publicar(EventoEnVivo(ids[0], "estado", estado=None))
        return await asyncio.gather(*tareas)

    resultados = asyncio.run(correr())
    assert resultados[0] is not None and resultados[0].tipo == "estado"
    assert all(r is None for r in resultados[1:])
