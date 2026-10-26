"""Envío de correos transaccionales con la API de Brevo (PB-06).

Documentación: POST https://api.brevo.com/v3/smtp/email con la cabecera
`api-key`. Se usa urllib (biblioteca estándar) para no sumar dependencias.
"""

import json
import urllib.error
import urllib.request

from app.ports.correo import ErrorEnvioCorreo, MensajeCorreo

URL_BREVO = "https://api.brevo.com/v3/smtp/email"
TIEMPO_ESPERA_SEGUNDOS = 10


class BrevoEnviador:
    def __init__(self, api_key: str, remitente_correo: str, remitente_nombre: str):
        self._api_key = api_key
        self._remitente = {"email": remitente_correo, "name": remitente_nombre}

    def enviar(self, mensaje: MensajeCorreo) -> None:
        cuerpo = {
            "sender": self._remitente,
            "to": [
                {
                    "email": mensaje.destinatario_correo,
                    "name": mensaje.destinatario_nombre,
                }
            ],
            "subject": mensaje.asunto,
            "htmlContent": mensaje.html,
            "textContent": mensaje.texto,
        }
        solicitud = urllib.request.Request(
            URL_BREVO,
            data=json.dumps(cuerpo).encode("utf-8"),
            method="POST",
            headers={
                "api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(solicitud, timeout=TIEMPO_ESPERA_SEGUNDOS):
                return
        except urllib.error.HTTPError as e:
            raise ErrorEnvioCorreo(f"Brevo respondió {e.code}: {_detalle(e)}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise ErrorEnvioCorreo(f"No se pudo conectar con Brevo: {e}") from e


def _detalle(error: urllib.error.HTTPError) -> str:
    """Mensaje de Brevo ({"code": ..., "message": ...}) sin exponer la clave."""
    try:
        datos = json.loads(error.read().decode("utf-8"))
        return str(datos.get("message") or datos.get("code") or error.reason)
    except (ValueError, AttributeError):
        return str(error.reason)
