"""Pruebas de integración del repositorio SQLAlchemy contra PostgreSQL.

Se saltan si no existe TEST_DATABASE_URL. Para correrlas en local, con la base
ya migrada (alembic upgrade head):

    TEST_DATABASE_URL=postgresql://usuario:clave@localhost:5432/nodovip pytest -q
"""

import os

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_escenarios import EscenarioModel
from app.adapters.outbound.persistence.models_sesiones import SesionModel
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.application.escenarios import ServicioEscenarios
from app.domain.escenarios import EstadoEscenario, Nivel
from app.ports.escenario_repository import FiltroBanco, FiltroEscenarios
from app.seed_escenarios import escenario_ransomware
from tests.pg import purgar_respuestas

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")


@pytest.fixture
def servicio():
    url = URL.replace("postgresql://", "postgresql+psycopg://", 1)
    with Session(create_engine(url)) as session:
        # Las sesiones apuntan a los escenarios (RESTRICT): se borran antes.
        purgar_respuestas(session)
        session.execute(delete(SesionModel))
        session.execute(delete(EscenarioModel))
        session.commit()
        yield ServicioEscenarios(
            SqlEscenarioRepository(session), SqlCatalogoRepository(session)
        )
        session.rollback()
        purgar_respuestas(session)
        session.execute(delete(SesionModel))
        session.execute(delete(EscenarioModel))
        session.commit()


def test_catalogo_cargado_por_la_migracion(servicio):
    tipos = {t.codigo for t in servicio.catalogo.tipos_escenario()}
    assert len(tipos) == 7
    assert "ransomware" in tipos
    assert len(servicio.catalogo.roles_ejercicio()) == 10


def test_guardar_publicar_y_leer_escenario_completo(servicio):
    creado = servicio.crear(escenario_ransomware())
    publicado = servicio.publicar(creado.id)
    leido = servicio.obtener(creado.id, puede_gestionar=False)
    assert publicado.estado == EstadoEscenario.PUBLICADO
    assert [i.orden for i in leido.injects] == [1, 2, 3, 4]
    assert len(leido.tareas) == 5
    assert leido.tareas[0].criterios[0].startswith("Aislar")


def test_actualizar_conserva_ids_y_reemplaza_contenido(servicio):
    creado = servicio.crear(escenario_ransomware())
    nuevo = escenario_ransomware()
    nuevo.tareas = creado.tareas[:]
    nuevo.tareas[0].enunciado = "Enunciado editado"
    nuevo.injects = nuevo.injects[:3]
    actualizado = servicio.actualizar(creado.id, nuevo)
    assert actualizado.tareas[0].id == creado.tareas[0].id
    assert actualizado.tareas[0].enunciado == "Enunciado editado"
    assert len(actualizado.injects) == 3


def test_filtros_y_banco(servicio):
    servicio.publicar(servicio.crear(escenario_ransomware()).id)
    borrador = escenario_ransomware()
    borrador.nombre = "Borrador sin publicar"
    servicio.crear(borrador)

    visibles = servicio.listar(FiltroEscenarios(), puede_gestionar=False)
    assert [e.nombre for e in visibles] == ["Ransomware en servidores de archivos"]
    assert servicio.listar(FiltroEscenarios(texto="SERVIDORES"), False)
    assert servicio.listar(FiltroEscenarios(rol_codigo="legal"), False)
    assert not servicio.listar(FiltroEscenarios(tipo_codigo="ddos"), False)

    banco = servicio.banco_de_preguntas(
        FiltroBanco(rol_codigo="legal", dificultad=Nivel.ALTO), puede_gestionar=False
    )
    assert len(banco) == 1
    assert banco[0].tipo_codigo == "ransomware"
