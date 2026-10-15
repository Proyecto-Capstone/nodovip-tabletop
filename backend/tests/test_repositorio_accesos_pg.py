"""Integración del historial de accesos con PostgreSQL (migración 0003).

Se saltan si no existe TEST_DATABASE_URL (ver test_repositorio_escenarios_pg.py).
"""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models import UsuarioModel
from app.adapters.outbound.persistence.models_accesos import AccesoModel
from app.adapters.outbound.persistence.repositorio_accesos import (
    SqlRegistroAccesoRepository,
)
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.domain.autenticacion import RegistroAcceso, ResultadoAcceso
from app.domain.usuarios import RolNombre, Usuario
from app.ports.autenticacion import FiltroAccesos

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")
DOMINIO = "%@accesos.prueba.test"
R = ResultadoAcceso


def _limpiar(session):
    session.execute(
        delete(AccesoModel).where(AccesoModel.correo_ingresado.like(DOMINIO))
    )
    session.execute(delete(UsuarioModel).where(UsuarioModel.correo.like(DOMINIO)))
    session.commit()


@pytest.fixture
def session():
    url = URL.replace("postgresql://", "postgresql+psycopg://", 1)
    with Session(create_engine(url)) as session:
        _limpiar(session)
        yield session
        session.rollback()
        _limpiar(session)


@pytest.fixture
def ana(session):
    return SqlUsuarioRepository(session).guardar(
        Usuario(
            correo="ana@accesos.prueba.test",
            nombre="Ana Pérez",
            password_hash="$2b$04$no-se-usa",
            rol=RolNombre.MODERADOR,
        )
    )


def _registrar(
    repo, resultado, minutos_atras, correo="ana@accesos.prueba.test", ana=None
):
    repo.registrar(
        RegistroAcceso(
            correo=correo,
            resultado=resultado,
            ip="2001:db8::1",
            usuario_id=ana.id if ana else None,
            user_agent="Pruebas",
            fecha_hora=datetime.now(UTC) - timedelta(minutes=minutos_atras),
        )
    )


def test_resultados_recientes_ordenados_y_sin_bloqueados(session, ana):
    repo = SqlRegistroAccesoRepository(session)
    _registrar(repo, R.EXITOSO, 30, ana=ana)  # fuera de la ventana
    _registrar(repo, R.CREDENCIALES_INVALIDAS, 10, ana=ana)
    _registrar(repo, R.BLOQUEADO, 5, ana=ana)
    _registrar(repo, R.USUARIO_INACTIVO, 1, ana=ana)
    desde = datetime.now(UTC) - timedelta(minutes=15)
    resultados = repo.resultados_recientes("ana@accesos.prueba.test", desde, 10)
    assert resultados == [R.USUARIO_INACTIVO, R.CREDENCIALES_INVALIDAS]
    assert repo.resultados_recientes("ana@accesos.prueba.test", desde, 1) == [
        R.USUARIO_INACTIVO
    ]


def test_listar_con_filtros(session, ana):
    repo = SqlRegistroAccesoRepository(session)
    _registrar(repo, R.EXITOSO, 3, ana=ana)
    _registrar(repo, R.CREDENCIALES_INVALIDAS, 2, correo="x@accesos.prueba.test")
    todos = repo.listar(FiltroAccesos(correo="accesos.prueba.test"))
    assert [r.resultado for r in todos] == [R.CREDENCIALES_INVALIDAS, R.EXITOSO]
    assert todos[0].usuario_id is None
    assert todos[1].ip == "2001:db8::1"
    assert todos[1].id is not None
    assert len(repo.listar(FiltroAccesos(usuario_id=ana.id))) == 1
    filtro = FiltroAccesos(correo="accesos.prueba.test", resultado=R.EXITOSO)
    assert len(repo.listar(filtro)) == 1
    hace_poco = datetime.now(UTC) - timedelta(minutes=2, seconds=30)
    filtro = FiltroAccesos(correo="accesos.prueba.test", desde=hace_poco)
    assert len(repo.listar(filtro)) == 1


def test_no_se_elimina_un_usuario_con_accesos(session, ana):
    _registrar(SqlRegistroAccesoRepository(session), R.EXITOSO, 1, ana=ana)
    with pytest.raises(IntegrityError):
        SqlUsuarioRepository(session).eliminar(ana.id)


def test_resultado_fuera_del_catalogo_lo_rechaza_la_base(session):
    session.add(
        AccesoModel(
            correo_ingresado="y@accesos.prueba.test", ip="10.0.0.1", resultado="otro"
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
