"""Integración del adaptador de Redis (PB-07).

Se salta si no existe TEST_REDIS_URL. En local, con Docker levantado:

    TEST_REDIS_URL=redis://:clave@localhost:6379/1 pytest -q tests/test_en_vivo_redis.py

Usa la base 1 de Redis para no tocar el estado de la aplicación (base 0).
"""

import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.redis import EnVivoRedis
from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo

URL = os.getenv("TEST_REDIS_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_REDIS_URL no definido")


@pytest.fixture
def redis_en_vivo():
    adaptador = EnVivoRedis(URL)
    sesion_id = uuid4()
    yield adaptador, sesion_id
    adaptador.eliminar(sesion_id)


def test_guardar_obtener_y_eliminar_el_estado(redis_en_vivo):
    adaptador, sesion_id = redis_en_vivo
    estado = EstadoEnVivo(sesion_id, total_injects=3, iniciada_en=datetime.now(UTC))
    estado.lanzar_siguiente_inject(datetime.now(UTC))

    adaptador.guardar(estado)
    assert adaptador.obtener(sesion_id) == estado

    adaptador.eliminar(sesion_id)
    assert adaptador.obtener(sesion_id) is None


def test_conexiones_por_usuario_con_varias_pestanas(redis_en_vivo):
    adaptador, sesion_id = redis_en_vivo
    ana, luis = uuid4(), uuid4()
    adaptador.conectar(sesion_id, ana)
    adaptador.conectar(sesion_id, ana)  # segunda pestaña
    adaptador.conectar(sesion_id, luis)
    assert adaptador.conectados(sesion_id) == {ana, luis}

    adaptador.desconectar(sesion_id, ana)
    assert adaptador.conectados(sesion_id) == {ana, luis}
    adaptador.desconectar(sesion_id, ana)
    assert adaptador.conectados(sesion_id) == {luis}


def test_pub_sub_entrega_el_evento(redis_en_vivo):
    adaptador, sesion_id = redis_en_vivo
    estado = EstadoEnVivo(sesion_id, total_injects=2, iniciada_en=datetime.now(UTC))

    async def escuchar_uno():
        eventos = adaptador.escuchar(sesion_id)
        assert (await anext(eventos)).tipo == "suscrito"
        adaptador.publicar(EventoEnVivo(sesion_id, "estado", estado=estado))
        recibido = await asyncio.wait_for(anext(eventos), timeout=3)
        await eventos.aclose()
        return recibido

    recibido = asyncio.run(escuchar_uno())
    assert recibido.tipo == "estado"
    assert recibido.estado == estado
