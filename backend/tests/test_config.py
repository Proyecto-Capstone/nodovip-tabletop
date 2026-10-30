"""Configuración de la sesión según el ambiente (PB-01)."""

import pytest

from app import config


def test_en_desarrollo_hay_secreto_por_defecto(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("JWT_SECRETO", raising=False)
    assert len(config.jwt_secreto()) >= config.JWT_SECRETO_MIN
    assert config.cookie_segura() is False


@pytest.mark.parametrize("ambiente", ["staging", "production"])
def test_fuera_de_desarrollo_el_secreto_es_obligatorio(monkeypatch, ambiente):
    monkeypatch.setenv("APP_ENV", ambiente)
    monkeypatch.setenv("JWT_SECRETO", "")
    with pytest.raises(RuntimeError, match="JWT_SECRETO"):
        config.verificar_configuracion()
    monkeypatch.setenv("JWT_SECRETO", "corto")
    with pytest.raises(RuntimeError, match="32"):
        config.verificar_configuracion()
    monkeypatch.setenv("JWT_SECRETO", "s" * 40)
    config.verificar_configuracion()


def test_sin_app_env_se_asume_servidor_real(monkeypatch):
    monkeypatch.delenv("APP_ENV")
    monkeypatch.delenv("JWT_SECRETO", raising=False)
    assert not config.es_desarrollo()
    with pytest.raises(RuntimeError):
        config.jwt_secreto()


def test_max_sesiones_activas_por_defecto(monkeypatch):
    monkeypatch.delenv("MAX_SESIONES_ACTIVAS", raising=False)
    assert config.max_sesiones_activas() == 10


def test_max_sesiones_activas_configurable(monkeypatch):
    monkeypatch.setenv("MAX_SESIONES_ACTIVAS", "25")
    assert config.max_sesiones_activas() == 25


@pytest.mark.parametrize("valor", ["0", "-3", "no-es-un-numero"])
def test_max_sesiones_activas_invalido_falla(monkeypatch, valor):
    monkeypatch.setenv("MAX_SESIONES_ACTIVAS", valor)
    with pytest.raises(RuntimeError, match="MAX_SESIONES_ACTIVAS"):
        config.max_sesiones_activas()


def test_cookie_segura(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SEGURA", "")
    assert config.cookie_segura() is True
    monkeypatch.setenv("COOKIE_SEGURA", "false")
    assert config.cookie_segura() is False
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("COOKIE_SEGURA", "true")
    assert config.cookie_segura() is True
