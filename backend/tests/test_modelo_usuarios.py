"""Pruebas del modelo de usuarios, roles y permisos (PC-11). No necesitan base de datos."""

import pytest

from app.adapters.outbound.persistence import models  # noqa: F401
from app.adapters.outbound.persistence.database import Base, get_database_url
from app.domain.usuarios import (
    PERMISOS_POR_ROL,
    PermisoCodigo,
    RolNombre,
    Usuario,
)


def test_existen_los_cinco_roles():
    assert {r.value for r in RolNombre} == {
        "administrador",
        "moderador",
        "participante",
        "observador",
        "analista",
    }


def test_cada_rol_tiene_permisos_definidos():
    assert set(PERMISOS_POR_ROL) == set(RolNombre)


def test_solo_administrador_gestiona_usuarios():
    con_permiso = [
        rol
        for rol, permisos in PERMISOS_POR_ROL.items()
        if PermisoCodigo.USUARIOS_GESTIONAR in permisos
    ]
    assert con_permiso == [RolNombre.ADMINISTRADOR]


def test_usuario_inactivo_no_tiene_permisos():
    usuario = Usuario(
        correo="admin@nodovip.test",
        nombre="Admin",
        password_hash="x",
        rol=RolNombre.ADMINISTRADOR,
        activo=False,
    )
    assert not usuario.tiene_permiso(PermisoCodigo.USUARIOS_GESTIONAR)


def test_observador_solo_ve_leaderboard():
    usuario = Usuario(
        correo="obs@nodovip.test",
        nombre="Obs",
        password_hash="x",
        rol=RolNombre.OBSERVADOR,
    )
    assert usuario.tiene_permiso(PermisoCodigo.LEADERBOARD_VER)
    assert not usuario.tiene_permiso(PermisoCodigo.SESIONES_PARTICIPAR)


def test_tablas_registradas_en_metadata():
    assert {"rol", "permiso", "rol_permiso", "usuario"} <= set(Base.metadata.tables)


def test_correo_de_usuario_es_unico():
    assert Base.metadata.tables["usuario"].c.correo.unique


def test_database_url_usa_psycopg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@postgres:5432/nodovip")
    assert get_database_url() == "postgresql+psycopg://u:p@postgres:5432/nodovip"


def test_database_url_faltante_lanza_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        get_database_url()
