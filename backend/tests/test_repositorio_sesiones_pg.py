"""Pruebas de integración del repositorio de sesiones contra PostgreSQL (PB-05).

Se saltan si no existe TEST_DATABASE_URL. Requieren la base migrada hasta 0004.
Borran sesiones y escenarios: después correr de nuevo `seed_escenarios`.
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
    EstadoInvitacion,
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    PesosPuntuacion,
    TipoTarea,
)
from app.domain.usuarios import RolNombre, Usuario
from app.seed_escenarios import escenario_ransomware
from tests.pg import purgar_respuestas

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")
DOMINIO = "%@sesiones.test"


def _limpiar(session: Session) -> None:
    session.rollback()
    # Las respuestas impiden borrar sesiones (RESTRICT): van primero.
    purgar_respuestas(session)
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


def test_invitaciones_se_guardan_y_el_participante_ve_su_sesion(entorno):
    servicio = entorno["servicio"]
    moderadora = entorno["moderadora"].id
    sesion = servicio.crear(entorno["escenario"].id, moderadora)
    sesion.participantes = [
        ParticipanteSesion(entorno[n].id, rol)
        for n, rol in zip(
            ["ana", "luis", "eva", "pia", "raul"], sesion.roles, strict=False
        )
    ]
    sesion.fecha_programada = datetime.now(UTC) + timedelta(days=5)
    sesion.duracion_minutos = 60
    servicio.actualizar(sesion.id, moderadora, sesion)
    sesion = servicio.programar(sesion.id, moderadora)

    ahora = datetime.now(UTC)
    sesion.participantes[0].marcar_enviada(ahora)
    sesion.participantes[1].marcar_fallida("Brevo respondió 400")
    servicio.repo.guardar(sesion)
    sesion.aceptar_invitacion(sesion.participantes[0].usuario_id, ahora)
    servicio.repo.guardar(sesion)

    leida = servicio.repo.obtener(sesion.id)
    por_usuario = {p.usuario_id: p for p in leida.participantes}
    primero = por_usuario[sesion.participantes[0].usuario_id]
    segundo = por_usuario[sesion.participantes[1].usuario_id]
    assert primero.invitacion == EstadoInvitacion.ACEPTADA
    assert primero.invitacion_enviada_en is not None
    assert primero.invitacion_aceptada_en is not None
    assert segundo.invitacion == EstadoInvitacion.FALLIDA
    assert segundo.invitacion_error == "Brevo respondió 400"

    de_ana = servicio.repo.listar_por_participante(entorno["ana"].id)
    assert [s.id for s in de_ana] == [sesion.id]
    assert servicio.repo.listar_por_participante(entorno["moderadora"].id) == []


def test_en_curso_guardar_no_recrea_tareas_y_la_respuesta_es_unica(entorno):
    """Las respuestas apuntan a las tareas: guardar una sesión en curso no
    debe borrarlas ni recrearlas (PB-08)."""
    from app.adapters.outbound.persistence.repositorio_respuestas import (
        SqlRespuestaRepository,
    )
    from app.domain.respuestas import Respuesta
    from app.ports.respuesta_repository import RespuestaDuplicada

    servicio = entorno["servicio"]
    moderadora = entorno["moderadora"].id
    sesion = servicio.crear(entorno["escenario"].id, moderadora)
    sesion.participantes = [
        ParticipanteSesion(entorno[n].id, rol)
        for n, rol in zip(
            ["ana", "luis", "eva", "pia", "raul"], sesion.roles, strict=False
        )
    ]
    sesion.fecha_programada = datetime.now(UTC) + timedelta(days=1)
    sesion.duracion_minutos = 60
    servicio.actualizar(sesion.id, moderadora, sesion)
    servicio.programar(sesion.id, moderadora)
    sesion = servicio.repo.obtener(sesion.id)
    ahora = datetime.now(UTC)
    sesion.iniciar(ahora)
    servicio.repo.guardar(sesion)

    participante = sesion.participantes[0]
    tarea = next(t for t in sesion.tareas if t.rol_codigo == participante.rol_codigo)
    respuestas = SqlRespuestaRepository(entorno["session"])
    nueva = Respuesta(
        sesion_id=sesion.id,
        tarea_id=tarea.id,
        inject_id=tarea.inject_id,
        usuario_id=participante.usuario_id,
        rol_codigo=participante.rol_codigo,
        recibida_en=ahora,
        segundos_usados=12,
        texto="Aíslo el file server",
    )
    respuestas.guardar(nueva)

    # Varios guardados en curso (lanzar injects, aceptar invitación) no tocan las tareas.
    ids_antes = [t.id for t in sesion.tareas]
    sesion.inject_actual = 2
    sesion.participantes[1].invitacion = EstadoInvitacion.ACEPTADA
    servicio.repo.guardar(sesion)
    leida = servicio.repo.obtener(sesion.id)
    assert [t.id for t in leida.tareas] == ids_antes
    assert leida.inject_actual == 2
    assert leida.participante_de(sesion.participantes[1].usuario_id).invitacion == (
        EstadoInvitacion.ACEPTADA
    )

    with pytest.raises(RespuestaDuplicada):
        respuestas.guardar(Respuesta(**{**vars(nueva), "id": uuid4(), "texto": "Otra"}))
    [guardada] = respuestas.de_participante(sesion.id, participante.usuario_id)
    assert guardada.texto == "Aíslo el file server" and guardada.segundos_usados == 12


def test_cliente_y_reporte_pdf_en_postgresql(entorno):
    """PB-14: la sesión guarda su cliente y el reporte guarda el último PDF."""
    from app.adapters.outbound.persistence.repositorio_reportes import (
        SqlReporteRepository,
    )
    from app.domain.reportes import EstadoReporte

    servicio = entorno["servicio"]
    sesion = servicio.crear(
        entorno["escenario"].id,
        entorno["moderadora"].id,
        "Con cliente",
        "  Banco   Andino ",
    )
    assert servicio.repo.obtener(sesion.id).cliente == "Banco Andino"

    reportes = SqlReporteRepository(entorno["session"])
    ahora = datetime.now(UTC)
    reportes.marcar_generando(sesion.id, ahora)
    assert reportes.obtener(sesion.id).estado == EstadoReporte.GENERANDO
    reportes.marcar_fallido(sesion.id, "Pango no disponible", ahora)
    assert reportes.obtener(sesion.id).error == "Pango no disponible"
    reportes.guardar_pdf(sesion.id, b"%PDF-1.7 prueba", ahora)
    guardado = reportes.obtener(sesion.id)
    assert guardado.estado == EstadoReporte.GENERADO and guardado.error is None
    assert guardado.pdf == b"%PDF-1.7 prueba"
    # La lista de estados no carga el PDF.
    [sin_pdf] = reportes.estados([sesion.id]).values()
    assert sin_pdf.pdf is None and sin_pdf.estado == EstadoReporte.GENERADO
