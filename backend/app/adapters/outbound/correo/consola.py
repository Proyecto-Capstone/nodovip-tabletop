"""Enviador para desarrollo: escribe el correo en el log en vez de enviarlo.

Se usa cuando no hay BREVO_API_KEY. Para ver los correos en local:
    docker compose logs -f backend
"""

import logging

from app.ports.correo import MensajeCorreo

log = logging.getLogger("nodovip.correo")


class ConsolaEnviador:
    def enviar(self, mensaje: MensajeCorreo) -> None:
        log.warning(
            "CORREO (no enviado, falta BREVO_API_KEY)\nPara: %s <%s>\nAsunto: %s\n\n%s",
            mensaje.destinatario_nombre,
            mensaje.destinatario_correo,
            mensaje.asunto,
            mensaje.texto,
        )
