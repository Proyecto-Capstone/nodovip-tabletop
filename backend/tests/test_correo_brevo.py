"""Adaptador de Brevo (PB-06) sin red: se reemplaza urlopen."""

import io
import json
import urllib.error

import pytest

from app.adapters.outbound import correo
from app.adapters.outbound.correo import brevo
from app.adapters.outbound.correo.brevo import BrevoEnviador
from app.adapters.outbound.correo.consola import ConsolaEnviador
from app.ports.correo import ErrorEnvioCorreo, MensajeCorreo

MENSAJE = MensajeCorreo(
    destinatario_correo="ana@prueba.test",
    destinatario_nombre="Ana López",
    asunto="Invitación",
    html="<p>Hola</p>",
    texto="Hola",
)


class RespuestaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_envia_el_correo_a_la_api_de_brevo(monkeypatch):
    llamadas = []

    def urlopen(solicitud, timeout):
        llamadas.append((solicitud, timeout))
        return RespuestaFalsa()

    monkeypatch.setattr(brevo.urllib.request, "urlopen", urlopen)
    BrevoEnviador("clave-de-prueba", "tabletop@nodovip.test", "NODOVIP").enviar(MENSAJE)

    [(solicitud, timeout)] = llamadas
    assert solicitud.full_url == "https://api.brevo.com/v3/smtp/email"
    assert solicitud.get_method() == "POST"
    assert solicitud.get_header("Api-key") == "clave-de-prueba"
    assert timeout == brevo.TIEMPO_ESPERA_SEGUNDOS
    cuerpo = json.loads(solicitud.data)
    assert cuerpo == {
        "sender": {"email": "tabletop@nodovip.test", "name": "NODOVIP"},
        "to": [{"email": "ana@prueba.test", "name": "Ana López"}],
        "subject": "Invitación",
        "htmlContent": "<p>Hola</p>",
        "textContent": "Hola",
    }


def test_un_error_de_brevo_se_convierte_en_error_de_envio(monkeypatch):
    def urlopen(solicitud, timeout):
        raise urllib.error.HTTPError(
            solicitud.full_url,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"code": "unauthorized", "message": "Key not found"}'),
        )

    monkeypatch.setattr(brevo.urllib.request, "urlopen", urlopen)
    with pytest.raises(ErrorEnvioCorreo, match="Brevo respondió 401: Key not found"):
        BrevoEnviador("mala", "a@b.test", "X").enviar(MENSAJE)


def test_sin_conexion_tambien_es_error_de_envio(monkeypatch):
    def urlopen(solicitud, timeout):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(brevo.urllib.request, "urlopen", urlopen)
    with pytest.raises(ErrorEnvioCorreo, match="No se pudo conectar con Brevo"):
        BrevoEnviador("clave", "a@b.test", "X").enviar(MENSAJE)


def test_sin_api_key_se_usa_la_consola(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    assert isinstance(correo.crear_enviador(), ConsolaEnviador)

    monkeypatch.setenv("BREVO_API_KEY", "clave")
    monkeypatch.setenv("CORREO_REMITENTE", "tabletop@nodovip.test")
    assert isinstance(correo.crear_enviador(), BrevoEnviador)


def test_la_consola_escribe_el_correo_en_el_log(caplog):
    ConsolaEnviador().enviar(MENSAJE)
    assert "ana@prueba.test" in caplog.text
    assert "Invitación" in caplog.text
