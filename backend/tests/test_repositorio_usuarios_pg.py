"""Integración del repositorio de usuarios con PostgreSQL y bcrypt real.

Se saltan si no existe TEST_DATABASE_URL (ver test_repositorio_escenarios_pg.py).
"""

import os

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models import UsuarioModel
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.adapters.outbound.seguridad.bcrypt_hasher import BcryptHasher
from app.application.usuarios import CorreoDuplicado, ServicioUsuarios
from app.domain.usuarios import RolNombre
from app.ports.usuario_repository import FiltroUsuarios

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")
CLAVE = "Nodovip2026seguro"


@pytest.fixture
def servicio():
    url = URL.replace("postgresql://", "postgresql+psycopg://", 1)
    with Session(create_engine(url)) as session:
        session.execute(
            delete(UsuarioModel).where(UsuarioModel.correo.like("%@prueba.test"))
        )
        session.commit()
        yield ServicioUsuarios(SqlUsuarioRepository(session), BcryptHasher(rondas=4))
        session.rollback()
        session.execute(
            delete(UsuarioModel).where(UsuarioModel.correo.like("%@prueba.test"))
        )
        session.commit()


def test_crear_guarda_hash_bcrypt_y_rol(servicio):
    usuario = servicio.crear("Ana Pérez", "Ana@Prueba.test", CLAVE, RolNombre.MODERADOR)
    leido = servicio.obtener(usuario.id)
    assert leido.correo == "ana@prueba.test"
    assert leido.rol == RolNombre.MODERADOR
    assert leido.password_hash.startswith("$2")
    assert BcryptHasher().verificar(CLAVE, leido.password_hash)
    assert leido.creado_en is not None


def test_correo_duplicado_sin_importar_mayusculas(servicio):
    servicio.crear("Ana Pérez", "ana@prueba.test", CLAVE, RolNombre.MODERADOR)
    with pytest.raises(CorreoDuplicado):
        servicio.crear("Otra Ana", "ANA@prueba.test", CLAVE, RolNombre.ANALISTA)


def test_filtros_cambio_de_rol_y_desactivar(servicio):
    ana = servicio.crear("Ana Pérez", "ana@prueba.test", CLAVE, RolNombre.MODERADOR)
    servicio.crear("Luis Mora", "luis@prueba.test", CLAVE, RolNombre.ANALISTA)

    assert len(servicio.listar(FiltroUsuarios(texto="prueba.test"))) == 2
    assert len(servicio.listar(FiltroUsuarios(texto="luis"))) == 1
    moderadores = servicio.listar(
        FiltroUsuarios(texto="prueba.test", rol=RolNombre.MODERADOR)
    )
    assert [u.nombre for u in moderadores] == ["Ana Pérez"]

    servicio.actualizar(ana.id, "Ana Pérez", "ana@prueba.test", RolNombre.OBSERVADOR)
    servicio.desactivar(ana.id)
    leida = servicio.obtener(ana.id)
    assert leida.rol == RolNombre.OBSERVADOR
    assert leida.activo is False
    inactivos = servicio.listar(FiltroUsuarios(texto="prueba.test", activo=False))
    assert [u.correo for u in inactivos] == ["ana@prueba.test"]


def test_eliminar_cuenta_desactivada(servicio):
    ana = servicio.crear("Ana Pérez", "ana@prueba.test", CLAVE, RolNombre.MODERADOR)
    servicio.desactivar(ana.id)
    servicio.eliminar(ana.id)
    assert servicio.repo.obtener_por_id(ana.id) is None
