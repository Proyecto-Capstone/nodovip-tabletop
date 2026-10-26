"""Adaptadores de salida para enviar correos (PB-06)."""

import logging

from app import config
from app.adapters.outbound.correo.brevo import BrevoEnviador
from app.adapters.outbound.correo.consola import ConsolaEnviador
from app.ports.correo import EnviadorCorreos

log = logging.getLogger(__name__)


def crear_enviador() -> EnviadorCorreos:
    """Brevo si hay BREVO_API_KEY; si no, el correo se escribe en el log."""
    clave = config.brevo_api_key()
    if clave:
        return BrevoEnviador(clave, *config.correo_remitente())
    if not config.es_desarrollo():
        log.warning("Falta BREVO_API_KEY: los correos no se envían, solo se registran")
    return ConsolaEnviador()
