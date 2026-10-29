"""Adaptadores del estado en vivo (PB-07): Redis en los servidores, memoria en pruebas.

Se crea una sola instancia por proceso: el pub/sub en memoria y el pool de
conexiones de Redis deben compartirse entre todos los requests.
"""

import logging
from functools import cache

from app import config
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.adapters.outbound.en_vivo.redis import EnVivoRedis

log = logging.getLogger(__name__)


@cache
def adaptador_en_vivo() -> EnVivoEnMemoria | EnVivoRedis:
    url = config.redis_url()
    if url:
        return EnVivoRedis(url)
    if not config.es_desarrollo():
        log.warning(
            "Falta REDIS_URL: el estado en vivo queda en memoria de un solo proceso"
        )
    return EnVivoEnMemoria()
