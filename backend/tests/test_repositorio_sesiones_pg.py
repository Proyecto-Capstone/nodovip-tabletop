"""Pruebas de integración del repositorio de sesiones contra PostgreSQL (PB-05).

Se saltan si no existe TEST_DATABASE_URL. Requieren la base migrada hasta 0004.
Borran sesiones y escenarios: después correr de nuevo `seed_escenarios`.
"""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models import UsuarioModel
from app.adapters.outbound.persistence.models_escenarios import EscenarioModel
from app.adapters.outbound.persistence.models_sesiones import SesionModel
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import (
    SqlSesionRepository,
)
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.escenarios import ServicioEscenarios
from app.application.sesiones import ServicioSesiones
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    PesosPuntuacion,
    TipoTarea,
)
from app.domain.usuarios import RolNombre, Usuario
from app.seed_escenarios import escenario_ransomware

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")
DOMINIO = "%@sesiones.test"


def _limpiar(session: Session) -> None:
    session.rollback()
    session.execute(delete(SesionModel))
    session.execute(delete(EscenarioModel))
    session.execute(delete(UsuarioModel).where(UsuarioModel.correo.like(DOMINIO)))
    session.commit()


@pytest.fixture
def entorno():
    url = URL.replace("postgresql://", "postgresql+psycopg://", 1)
    with Session(create_engine(url)) as session:
        _limpiar(session)
        usuarios = SqlUsuarioRepository(session)
        nuevos = {
            nombre: usuarios.guardar(
                Usuario(
                    correo=f"{nombre}@sesiones.test",
                    nombre=nombre.title(),
                    password_hash="x",
                    rol=rol,
                )
            )
            for nombre, rol in [
                ("moderadora", RolNombre.MODERADOR),
                ("ana", RolNombre.PARTICIPANTE),
                ("luis", RolNombre.PARTICIPANTE),
                ("eva", RolNombre.PARTICIPANTE),
                ("pia", RolNombre.PARTICIPANTE),
                ("raul", RolNombre.PARTICIPANTE),
            ]
        }
        catalogo = SqlCatalogoRepository(session)
        escenarios = ServicioEscenarios(SqlEscenarioRepository(session), catalogo)
        escenario = escenarios.crear(escenario_ransomware())
        escenarios.publicar(escenario.id)
        servicio = ServicioSesiones(
            SqlSesionRepository(session),
            SqlEscenarioRepository(session),
            catalogo,
            usuarios,
        )
        yield {
            "servicio": servicio,
            "escenario": escenario,
            "session": session,
            **nuevos,
        }
        _limpiar(session)


def test_crear_programar_y_leer_sesion_completa(entorno):
    servicio = entorno["servicio"]
    moderadora = entorno["moderadora"].id
    sesion = servicio.crear(entorno["escenario"].id, moderadora, "Simulacro Q4")

    participantes = ["ana", "luis", "eva", "pia", "raul"]
    sesion.participantes = [
        ParticipanteSesion(entorno[nombre].id, rol)
        for nombre, rol in zip(participantes, sesion.roles, strict=False)
    ]
    tarea = sesion.tareas[0]
    tarea.tipo = TipoTarea.SELECCION_MULTIPLE
    tarea.opciones = [
        OpcionRespuesta("Aislar", correcta=True),
        OpcionRespuesta("Pagar"),
    ]
    sesion.pesos = PesosPuntuacion(50, 30, 20)
    sesion.fecha_programada = datetime.now(UTC) + timedelta(days=5)
    sesion.duracion_minutos = 120
    servicio.actualizar(sesion.id, moderadora, sesion)
    servicio.programar(sesion.id, moderadora)

    leida = servicio.obtener(sesion.id, moderadora)
    assert leida.estado == EstadoSesion.PROGRAMADA
    assert leida.nombre == "Simulacro Q4"
    assert len(leida.participantes) == len(sesion.roles)
    assert leida.pesos == PesosPuntuacion(50, 30, 20)
    assert leida.tareas[0].opciones[0] == OpcionRespuesta("Aislar", correcta=True)
    assert {t.inject_id for t in leida.tareas} <= {i.id for i in leida.injects}
    assert [s.id for s in servicio.listar(moderadora)] == [sesion.id]


def test_guardar_reemplaza_injects_y_tareas_conservando_ids(entorno):
    servicio = entorno["servicio"]
    moderadora = entorno["moderadora"].id
    sesion = servicio.crear(entorno["escenario"].id, moderadora)
    ids_tareas = [t.id for t in sesion.tareas]

    # Se quita el primer inject: sus tareas pasan al segundo.
    primero, segundo = sesion.injects[0], sesion.injects[1]
    sesion.injects = sesion.injects[1:]
    for pos, inject in enumerate(sesion.injects, start=1):
        inject.orden = pos
    for t in sesion.tareas:
        if t.inject_id == primero.id:
            t.inject_id = segundo.id
    servicio.actualizar(sesion.id, moderadora, sesion)

    leida = servicio.obtener(sesion.id, moderadora)
    assert [i.orden for i in leida.injects] == list(range(1, len(sesion.injects) + 1))
    assert [t.id for t in leida.tareas] == ids_tareas
    assert primero.id not in {t.inject_id for t in leida.tareas}


def test_un_participante_asignado_no_se_puede_eliminar(entorno):
    servicio = entorno["servicio"]
    moderadora = entorno["moderadora"].id
    sesion = servicio.crear(entorno["escenario"].id, moderadora)
    sesion.participantes = [ParticipanteSesion(entorno["ana"].id, sesion.roles[0])]
    servicio.actualizar(sesion.id, moderadora, sesion)

    with pytest.raises(IntegrityError):
        servicio.usuarios.eliminar(entorno["ana"].id)


def test_eliminar_borrador_borra_su_contenido(entorno):
    servicio = entorno["servicio"]
    moderadora = entorno["moderadora"].id
    sesion = servicio.crear(entorno["escenario"].id, moderadora)

    servicio.eliminar(sesion.id, moderadora)

    assert servicio.repo.obtener(sesion.id) is None
