"""Registro trazable de respuestas contra PostgreSQL (PB-09).

Se saltan si no existe TEST_DATABASE_URL (base nodovip_test migrada hasta 0008).

- La base rechaza modificar o borrar respuestas, aunque se use SQL directo.
- Con muchos participantes respondiendo a la vez no se pierde ninguna, y un
  participante que envía dos veces a la vez queda con una sola respuesta.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, delete, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.adapters.outbound.persistence.models import UsuarioModel
from app.adapters.outbound.persistence.models_escenarios import EscenarioModel
from app.adapters.outbound.persistence.models_sesiones import SesionModel
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_respuestas import (
    SqlRespuestaRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.en_vivo import ServicioEnVivo
from app.application.escenarios import ServicioEscenarios
from app.application.respuestas import ServicioRegistroRespuestas, ServicioRespuestas
from app.application.sesiones import ServicioSesiones
from app.domain.sesiones import ParticipanteSesion, TareaSesion, TipoTarea
from app.domain.usuarios import RolNombre, Usuario
from app.ports.respuesta_repository import RespuestaDuplicada
from app.seed_escenarios import escenario_ransomware
from tests.pg import purgar_respuestas

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")
DOMINIO = "%@respuestas.test"
PARTICIPANTES = 20


def _limpiar(session: Session) -> None:
    session.rollback()
    purgar_respuestas(session)
    session.execute(delete(SesionModel))
    session.execute(delete(EscenarioModel))
    session.execute(delete(UsuarioModel).where(UsuarioModel.correo.like(DOMINIO)))
    session.commit()


@pytest.fixture
def entorno():
    """Una sesión en curso con todos sus injects lanzados y 20 participantes."""
    url = URL.replace("postgresql://", "postgresql+psycopg://", 1)
    # Una conexión por participante, para que de verdad escriban a la vez.
    engine = create_engine(url, pool_size=PARTICIPANTES + 2)
    with Session(engine) as session:
        _limpiar(session)
        usuarios = SqlUsuarioRepository(session)
        moderadora = usuarios.guardar(
            Usuario(
                "moderadora@respuestas.test", "Moderadora", "x", RolNombre.MODERADOR
            )
        )
        participantes = [
            usuarios.guardar(
                Usuario(
                    f"p{i:02}@respuestas.test",
                    f"Participante {i:02}",
                    "x",
                    RolNombre.PARTICIPANTE,
                )
            )
            for i in range(PARTICIPANTES)
        ]
        catalogo = SqlCatalogoRepository(session)
        escenarios = ServicioEscenarios(SqlEscenarioRepository(session), catalogo)
        escenario = escenarios.crear(escenario_ransomware())
        escenarios.publicar(escenario.id)
        sesiones = ServicioSesiones(
            SqlSesionRepository(session),
            SqlEscenarioRepository(session),
            catalogo,
            usuarios,
        )
        sesion = sesiones.crear(escenario.id, moderadora.id, "Concurrencia")
        # Varios participantes por rol: todos los roles quedan cubiertos.
        sesion.participantes = [
            ParticipanteSesion(p.id, sesion.roles[i % len(sesion.roles)])
            for i, p in enumerate(participantes)
        ]
        sesion.fecha_programada = datetime.now(UTC) + timedelta(days=1)
        sesion.duracion_minutos = 60
        sesiones.actualizar(sesion.id, moderadora.id, sesion)
        sesiones.programar(sesion.id, moderadora.id)

        almacen = EnVivoEnMemoria()
        en_vivo = ServicioEnVivo(SqlSesionRepository(session), almacen)
        en_vivo.iniciar(sesion.id, moderadora.id)
        for _ in sesion.injects:
            en_vivo.lanzar_inject(sesion.id, moderadora.id)

        yield {
            "engine": engine,
            "almacen": almacen,
            "session": session,
            "sesion": sesiones.repo.obtener(sesion.id),
            "moderadora": moderadora,
            "participantes": participantes,
        }
        _limpiar(session)
    engine.dispose()


def _tarea_de(sesion, usuario_id) -> TareaSesion:
    rol = sesion.participante_de(usuario_id).rol_codigo
    return next(t for t in sesion.tareas if t.rol_codigo == rol)


def _contenido(tarea: TareaSesion, texto: str) -> tuple[str | None, list[int]]:
    if tarea.tipo == TipoTarea.SELECCION_MULTIPLE:
        return None, [0]
    return texto, []


def _responder(e, usuario_id, texto):
    """Lo que hace un request: su propia conexión y su propio servicio."""
    tarea = _tarea_de(e["sesion"], usuario_id)
    with Session(e["engine"]) as s:
        servicio = ServicioRespuestas(
            SqlSesionRepository(s), e["almacen"], SqlRespuestaRepository(s)
        )
        return servicio.responder(
            e["sesion"].id, usuario_id, tarea.id, *_contenido(tarea, texto)
        )


def _a_la_vez(funciones):
    """Lanza todas las funciones juntas; devuelve el resultado o la excepción."""
    barrera = threading.Barrier(len(funciones))

    def correr(f):
        barrera.wait()
        return f()

    with ThreadPoolExecutor(len(funciones)) as ex:
        futuros = [ex.submit(correr, f) for f in funciones]
        return [f.exception() or f.result() for f in futuros]


def test_no_se_pierden_respuestas_con_participantes_enviando_a_la_vez(entorno):
    e = entorno
    resultados = _a_la_vez(
        [
            lambda p=p: _responder(e, p.id, f"Respuesta de {p.nombre}")
            for p in e["participantes"]
        ]
    )
    errores = [r for r in resultados if isinstance(r, Exception)]
    assert errores == []

    guardadas = SqlRespuestaRepository(e["session"]).de_sesion(e["sesion"].id)
    assert len(guardadas) == PARTICIPANTES
    assert {r.usuario_id for r in guardadas} == {p.id for p in e["participantes"]}
    for r in guardadas:
        nombre = next(p.nombre for p in e["participantes"] if p.id == r.usuario_id)
        assert r.texto in (None, f"Respuesta de {nombre}")
        assert r.rol_codigo == e["sesion"].participante_de(r.usuario_id).rol_codigo
    # En orden de llegada.
    assert [r.recibida_en for r in guardadas] == sorted(
        r.recibida_en for r in guardadas
    )


def test_doble_envio_simultaneo_queda_con_una_sola_respuesta(entorno):
    e = entorno
    ana = e["participantes"][0]
    resultados = _a_la_vez(
        [lambda i=i: _responder(e, ana.id, f"Intento {i}") for i in range(10)]
    )
    exitos = [r for r in resultados if not isinstance(r, Exception)]
    duplicadas = [r for r in resultados if isinstance(r, RespuestaDuplicada)]
    assert len(exitos) == 1 and len(duplicadas) == 9

    [guardada] = SqlRespuestaRepository(e["session"]).de_participante(
        e["sesion"].id, ana.id
    )
    assert guardada.id == exitos[0].id and guardada.texto == exitos[0].texto


def test_la_base_impide_modificar_o_borrar_respuestas(entorno):
    e = entorno
    ana = e["participantes"][0]
    original = _responder(e, ana.id, "Aíslo el servidor")
    session = e["session"]

    for sql in (
        "UPDATE respuesta SET texto = 'Pago el rescate'",
        "UPDATE respuesta SET recibida_en = now() - interval '1 hour'",
        "DELETE FROM respuesta",
        "TRUNCATE respuesta",
    ):
        with pytest.raises(DBAPIError, match="no se pueden modificar ni borrar"):
            session.execute(text(sql))
        session.rollback()

    # Ni siquiera la marca de purga permite modificar: solo borrar.
    session.execute(text("SET LOCAL nodovip.purgar_respuestas = 'si'"))
    with pytest.raises(DBAPIError, match="no se pueden modificar ni borrar"):
        session.execute(text("UPDATE respuesta SET texto = 'Otra'"))
    session.rollback()

    [guardada] = SqlRespuestaRepository(session).de_sesion(e["sesion"].id)
    assert guardada.texto == original.texto
    assert guardada.recibida_en == original.recibida_en


def test_registro_de_la_sesion_con_nombres_y_roles(entorno):
    e = entorno
    for p in e["participantes"][:3]:
        _responder(e, p.id, f"Respuesta de {p.nombre}")
    session = e["session"]
    registro = ServicioRegistroRespuestas(
        SqlSesionRepository(session),
        SqlRespuestaRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
    ).de_sesion(e["sesion"].id, e["moderadora"].id)

    assert [r.participante_nombre for r in registro] == [
        "Participante 00",
        "Participante 01",
        "Participante 02",
    ]
    roles = {
        r.codigo: r.nombre for r in SqlCatalogoRepository(session).roles_ejercicio()
    }
    for r in registro:
        assert r.rol_nombre == roles[r.respuesta.rol_codigo]
        assert r.inject_titulo and r.tarea.id == r.respuesta.tarea_id
