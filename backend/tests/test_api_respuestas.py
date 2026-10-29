"""API de tareas y respuestas del participante (PB-08) con dobles en memoria."""

from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import en_vivo, mis_sesiones
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.application.respuestas import ServicioRespuestas
from app.domain.escenarios import Inject, Nivel
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)
from app.main import app
from tests.fakes import RepoRespuestasEnMemoria, RepoSesionesEnMemoria

MODERADOR = {"X-Rol-Prueba": "moderador"}
PARTICIPANTE = {"X-Rol-Prueba": "participante"}
ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
ID_PARTICIPANTE = uuid5(NAMESPACE_URL, "prueba:participante")


@pytest.fixture
def e(sesion_por_cabecera):
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    sesion = SesionTabletop(
        nombre="Simulacro",
        escenario_id=uuid4(),
        moderador_id=ID_MODERADOR,
        roles=["ti", "legal"],
        injects=[i1],
        tareas=[
            TareaSesion(
                "¿Paga el rescate?",
                "ti",
                Nivel.ALTO,
                [],
                inject_id=i1.id,
                tipo=TipoTarea.SELECCION_MULTIPLE,
                opciones=[OpcionRespuesta("No", correcta=True), OpcionRespuesta("Sí")],
            ),
            TareaSesion(
                "¿A quién notifica?",
                "legal",
                Nivel.BAJO,
                ["Regulador"],
                inject_id=i1.id,
            ),
        ],
        participantes=[
            ParticipanteSesion(ID_PARTICIPANTE, "ti"),
            ParticipanteSesion(uuid4(), "legal"),
        ],
        estado=EstadoSesion.PROGRAMADA,
    )
    repo = RepoSesionesEnMemoria()
    repo.guardar(sesion)
    almacen = EnVivoEnMemoria()
    app.dependency_overrides[en_vivo.get_servicio_en_vivo] = lambda: ServicioEnVivo(
        repo, almacen
    )
    servicio = ServicioRespuestas(repo, almacen, RepoRespuestasEnMemoria())
    app.dependency_overrides[mis_sesiones.get_servicio_respuestas] = lambda: servicio
    with TestClient(app) as client:
        yield {"client": client, "sesion": sesion}
    app.dependency_overrides.pop(en_vivo.get_servicio_en_vivo, None)
    app.dependency_overrides.pop(mis_sesiones.get_servicio_respuestas, None)


def _iniciar_y_lanzar(e):
    for accion in ("iniciar", "lanzar-inject"):
        r = e["client"].post(
            f"/api/sesiones/{e['sesion'].id}/en-vivo/{accion}", headers=MODERADOR
        )
        assert r.status_code == 200, r.text


def _url(e, tarea=None):
    base = f"/api/mis-sesiones/{e['sesion'].id}/tareas"
    return f"{base}/{tarea.id}/respuesta" if tarea else base


def test_el_participante_ve_sus_tareas_sin_la_respuesta_correcta(e):
    assert e["client"].get(_url(e), headers=PARTICIPANTE).json() == []
    _iniciar_y_lanzar(e)

    [t] = e["client"].get(_url(e), headers=PARTICIPANTE).json()
    assert t["enunciado"] == "¿Paga el rescate?"
    assert t["opciones"] == ["No", "Sí"]  # solo el texto
    assert t["estado"] == "pendiente" and t["respuesta"] is None
    assert "correcta" not in str(t) and "criterios" not in t


def test_responder_una_vez(e):
    _iniciar_y_lanzar(e)
    tarea = e["sesion"].tareas[0]

    r = e["client"].post(_url(e, tarea), json={"opciones": [0]}, headers=PARTICIPANTE)
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "respondida"
    assert r.json()["respuesta"]["opciones_elegidas"] == [0]

    r = e["client"].post(_url(e, tarea), json={"opciones": [1]}, headers=PARTICIPANTE)
    assert r.status_code == 409
    assert "no se puede cambiar" in r.json()["detail"]


def test_errores_de_validacion(e):
    _iniciar_y_lanzar(e)
    tarea = e["sesion"].tareas[0]
    r = e["client"].post(
        _url(e, tarea), json={"texto": "No pago"}, headers=PARTICIPANTE
    )
    assert r.status_code == 422
    assert r.json()["detail"]["errores"] == [
        "Esta tarea se responde eligiendo opciones"
    ]


def test_tareas_de_otro_rol_responden_404(e):
    _iniciar_y_lanzar(e)
    de_legal = e["sesion"].tareas[1]
    r = e["client"].post(
        _url(e, de_legal), json={"texto": "Al regulador"}, headers=PARTICIPANTE
    )
    assert r.status_code == 404


def test_solo_participantes(e):
    assert e["client"].get(_url(e)).status_code == 401
    assert e["client"].get(_url(e), headers=MODERADOR).status_code == 403
