"""Política de contraseñas y normalización de correos (PB-02)."""

import pytest

from app.adapters.outbound.seguridad.bcrypt_hasher import BcryptHasher
from app.domain.usuarios import (
    ReglaUsuarioError,
    errores_contrasena,
    normalizar_correo,
    validar_contrasena,
)


def test_contrasena_valida():
    assert errores_contrasena("Nodovip2026seguro") == []


@pytest.mark.parametrize(
    ("contrasena", "esperado"),
    [
        ("Corta1", "al menos 10"),
        ("sinmayusculas123", "mayúscula"),
        ("SINMINUSCULAS123", "minúscula"),
        ("SinNumerosAqui", "número"),
        (" Espacio12345", "espacios"),
        ("Aa1" + "x" * 80, "72 bytes"),
    ],
)
def test_contrasena_invalida(contrasena, esperado):
    assert any(esperado in e for e in errores_contrasena(contrasena))


def test_validar_contrasena_lanza_error():
    with pytest.raises(ReglaUsuarioError):
        validar_contrasena("debil")


def test_correo_se_normaliza():
    assert normalizar_correo("  Ana.Perez@NodoVIP.test ") == "ana.perez@nodovip.test"


def test_bcrypt_hashea_y_verifica():
    hasher = BcryptHasher(rondas=4)
    hash_guardado = hasher.hashear("Nodovip2026seguro")
    assert hash_guardado.startswith("$2")
    assert "Nodovip2026seguro" not in hash_guardado
    assert hasher.verificar("Nodovip2026seguro", hash_guardado)
    assert not hasher.verificar("OtraClave2026", hash_guardado)
    assert not hasher.verificar("Nodovip2026seguro", "no-es-un-hash")
