"""Puerto de salida para enviar correos (PB-06).

Los casos de uso dependen de esta interfaz, nunca de Brevo: el adaptador se
puede cambiar sin tocar el dominio.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MensajeCorreo:
    destinatario_correo: str
    destinatario_nombre: str
    asunto: str
    html: str
    texto: str


class ErrorEnvioCorreo(Exception):
    """El proveedor no aceptó el correo (o no respondió)."""


class EnviadorCorreos(Protocol):
    def enviar(self, mensaje: MensajeCorreo) -> None:
        """Envía el correo o lanza ErrorEnvioCorreo."""
        ...
