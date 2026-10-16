"""Adaptador de tokens JWT (PB-01)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.adapters.outbound.seguridad.jwt_tokens import JwtTokens

SECRETO = "secreto-de-prueba-de-al-menos-32-caracteres"


def test_token_valido_devuelve_el_usuario():
    usuario_id = uuid4()
    tokens = JwtTokens(SECRETO)
    assert tokens.validar(tokens.emitir(usuario_id)) == usuario_id


def test_token_vencido_es_invalido():
    hace_9_horas = datetime.now(UTC) - timedelta(hours=9)
    viejo = JwtTokens(SECRETO, reloj=lambda: hace_9_horas)
    assert JwtTokens(SECRETO).validar(viejo.emitir(uuid4())) is None


def test_token_alterado_es_invalido():
    token = JwtTokens(SECRETO).emitir(uuid4())
    cabecera, datos, firma = token.split(".")
    alterado = f"{cabecera}.{datos}.{firma[:-2]}xx"
    assert JwtTokens(SECRETO).validar(alterado) is None


def test_token_firmado_con_otro_secreto_es_invalido():
    ajeno = JwtTokens("otro-secreto-distinto-de-al-menos-32-car").emitir(uuid4())
    assert JwtTokens(SECRETO).validar(ajeno) is None


def test_no_acepta_alg_none_ni_basura():
    sin_firma = jwt.encode(
        {"sub": str(uuid4()), "iat": datetime.now(UTC), "exp": datetime.now(UTC)},
        key=None,
        algorithm="none",
    )
    tokens = JwtTokens(SECRETO)
    assert tokens.validar(sin_firma) is None
    assert tokens.validar("no-es-un-jwt") is None
    assert tokens.validar("") is None


def test_sub_que_no_es_uuid_es_invalido():
    ahora = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "admin", "iat": ahora, "exp": ahora + timedelta(hours=1)},
        SECRETO,
        algorithm="HS256",
    )
    assert JwtTokens(SECRETO).validar(token) is None
