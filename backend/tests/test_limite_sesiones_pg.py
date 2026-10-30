"""Límite de sesiones activas bajo concurrencia real (PC-24, RNF).

Se salta si no existe TEST_DATABASE_URL (base nodovip_test migrada).

Lanza 12 arranques de sesión a la vez contra un límite de 10, cada uno con
su propia conexión de PostgreSQL (igual que 12 requests distintos). Esto
ejercita de verdad el supuesto documentado en
`SqlSesionRepository.iniciar_si_hay_cupo`: la sesión de SQLAlchemy usa el
nivel de aislamiento por defecto de PostgreSQL (READ COMMITTED, sin
`isolation_level` fijado en `database.py`), así que el conteo dentro del
advisory lock ve lo que ya confirmaron las demás transacciones en vez de
una foto de antes de pedir el lock. Si esto no se cumpliera, sería posible
terminar con más de 10 sesiones en_curso.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.adapters.outbound.persistence.models import UsuarioModel
from app.adapters.outbound.persistence.models_escenarios import EscenarioModel
from app.adapters.outbound.persistence.models_sesiones import SesionModel
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.en_vivo import ServicioEnVivo
from app.application.escenarios import ServicioEscenarios
from app.application.sesiones import ServicioSesiones
from app.domain.sesiones import EstadoSesion, ParticipanteSesion, ReglaSesionError
from app.domain.usuarios import RolNombre, Usuario
from app.seed_escenarios import escenario_ransomware

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")
DOMINIO = "%@limite.test"
N_SESIONES = 12
MAXIMO_ACTIVAS = 10


def _limpiar(session: Session) -> None:
    session.rollback()
    session.execute(delete(SesionModel))
    session.execute(delete(EscenarioModel))
    session.execute(delete(UsuarioModel).where(UsuarioModel.correo.like(DOMINIO)))
    session.commit()


@pytest.fixture
def entorno():
    """N_SESIONES sesiones PROGRAMADA, cada una con su propio moderador."""
    url = URL.replace("postgresql://", "postgresql+psycopg://", 1)
    # Una conexión por sesión, para que arranquen de verdad a la vez.
    engine = create_engine(url, pool_size=N_SESIONES + 2)
    with Session(engine) as session:
        _limpiar(session)
        usuarios = SqlUsuarioRepository(session)
        catalogo = SqlCatalogoRepository(session)
        escenarios = ServicioEscenarios(SqlEscenarioRepository(session), catalogo)
        escenario = escenarios.crear(escenario_ransomware())
        escenarios.publicar(escenario.id)
        sesiones_app = ServicioSesiones(
            SqlSesionRepository(session),
            SqlEscenarioRepository(session),
            catalogo,
            usuarios,
        )
        # Un participante por rol, compartido entre las N_SESIONES: alcanza
        # para programar (cada sesión exige al menos uno por rol).
        participantes = [
            usuarios.guardar(
                Usuario(
                    f"p{i:02}@limite.test",
                    f"Participante {i:02}",
                    "x",
                    RolNombre.PARTICIPANTE,
                )
            )
            for i in range(len(escenario.roles))
        ]

        pares = []
        for i in range(N_SESIONES):
            moderador = usuarios.guardar(
                Usuario(
                    f"mod{i:02}@limite.test",
                    f"Moderador {i:02}",
                    "x",
                    RolNombre.MODERADOR,
                )
            )
            sesion = sesiones_app.crear(escenario.id, moderador.id, f"Simulacro {i:02}")
            sesion.participantes = [
                ParticipanteSesion(p.id, rol)
                for p, rol in zip(participantes, escenario.roles, strict=True)
            ]
            sesion.fecha_programada = datetime.now(UTC) + timedelta(days=1)
            sesion.duracion_minutos = 60
            sesiones_app.actualizar(sesion.id, moderador.id, sesion)
            sesiones_app.programar(sesion.id, moderador.id)
            pares.append((sesion.id, moderador.id))

        yield {"engine": engine, "almacen": EnVivoEnMemoria(), "pares": pares}
        _limpiar(session)
    engine.dispose()


def _iniciar(e, sesion_id, moderador_id):
    """Lo que hace un arranque: su propia conexión, igual que un request real."""
    with Session(e["engine"]) as session:
        servicio = ServicioEnVivo(
            SqlSesionRepository(session),
            e["almacen"],
            maximo_activas=MAXIMO_ACTIVAS,
        )
        return servicio.iniciar(sesion_id, moderador_id)


def _a_la_vez(funciones):
    """Lanza todas las funciones juntas; devuelve el resultado o la excepción."""
    barrera = threading.Barrier(len(funciones))

    def correr(f):
        barrera.wait()
        return f()

    with ThreadPoolExecutor(len(funciones)) as ex:
        futuros = [ex.submit(correr, f) for f in funciones]
        return [f.exception() or f.result() for f in futuros]


def test_doce_arranques_a_la_vez_nunca_superan_el_maximo(entorno):
    e = entorno
    resultados = _a_la_vez(
        [lambda sid=sid, mid=mid: _iniciar(e, sid, mid) for sid, mid in e["pares"]]
    )

    exitos = [r for r in resultados if not isinstance(r, Exception)]
    errores = [r for r in resultados if isinstance(r, Exception)]
    assert len(exitos) == MAXIMO_ACTIVAS
    assert len(errores) == N_SESIONES - MAXIMO_ACTIVAS
    assert all(isinstance(err, ReglaSesionError) for err in errores)
    assert all(
        f"máximo de {MAXIMO_ACTIVAS} sesiones activas" in str(err) for err in errores
    )

    with Session(e["engine"]) as session:
        activas = session.scalar(
            select(func.count())
            .select_from(SesionModel)
            .where(SesionModel.estado == EstadoSesion.EN_CURSO.value)
        )
    assert activas == MAXIMO_ACTIVAS
