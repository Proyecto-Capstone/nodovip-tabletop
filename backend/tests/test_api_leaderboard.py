"""API y WebSocket del leaderboard (PB-12) con dobles en memoria."""

import time
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import en_vivo, mis_sesiones
from app.adapters.inbound.api import leaderboard as api_leaderboard
from app.adapters.inbound.api import respuestas as api_respuestas
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.application.leaderboard import ServicioLeaderboard
from app.application.respuestas import ServicioRegistroRespuestas, ServicioRespuestas
from app.domain.en_vivo import EventoEnVivo
from app.domain.escenarios import Inject, Nivel, RolEjercicio
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)
from app.domain.usuarios import RolNombre, Usuario
from app.main import app
from tests.fakes import (
    RepoRespuestasEnMemoria,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

MODERADOR = {"X-Rol-Prueba": "moderador"}
PARTICIPANTE = {"X-Rol-Prueba": "participante"}
OBSERVADOR = {"X-Rol-Prueba": "observador"}
ADMINISTRADOR = {"X-Rol-Prueba": "administrador"}
ANALISTA = {"X-Rol-Prueba": "analista"}

ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
ID_PARTICIPANTE = uuid5(NAMESPACE_URL, "prueba:participante")


class CatalogoFalso:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


def _sesion(estado=EstadoSesion.PROGRAMADA, moderador_id=ID_MODERADOR):
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    return SesionTabletop(
        nombre="Simulacro",
        escenario_id=uuid4(),
        moderador_id=moderador_id,
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
                opciones=[
                    OpcionRespuesta("No paga nunca el rescate", correcta=True),
                    OpcionRespuesta("Sí, para recuperar los archivos"),
                ],
            ),
            TareaSesion(
                "¿A quién notifica?",
                "legal",
                Nivel.BAJO,
                ["Regulador"],
                inject_id=i1.id,
            ),
        ],
        participantes=[ParticipanteSesion(ID_PARTICIPANTE, "ti")],
        estado=estado,
    )


@pytest.fixture
def e(sesion_por_cabecera):
    sesion = _sesion(EstadoSesion.PROGRAMADA)
    repo = RepoSesionesEnMemoria()
    repo.guardar(sesion)
    almacen = EnVivoEnMemoria()
    app.dependency_overrides[en_vivo.get_servicio_en_vivo] = lambda: ServicioEnVivo(
        repo, almacen
    )
    app.dependency_overrides[en_vivo.get_suscriptor] = lambda: almacen
    respuestas = RepoRespuestasEnMemoria()
    servicio_respuestas = ServicioRespuestas(repo, almacen, respuestas)
    app.dependency_overrides[mis_sesiones.get_servicio_respuestas] = lambda: (
        servicio_respuestas
    )
    usuarios = RepoUsuariosEnMemoria()
    usuarios.guardar(
        Usuario(
            "ana@demo.nodovip.test",
            "Ana López",
            "hash",
            RolNombre.PARTICIPANTE,
            id=ID_PARTICIPANTE,
        )
    )
    registro = ServicioRegistroRespuestas(
        repo, respuestas, CatalogoFalso(), usuarios, almacen
    )
    app.dependency_overrides[api_respuestas.get_servicio_registro] = lambda: registro

    servicio_leaderboard = ServicioLeaderboard(
        repo, respuestas, CatalogoFalso(), usuarios, almacen
    )
    app.dependency_overrides[api_leaderboard.get_servicio_leaderboard] = lambda: (
        servicio_leaderboard
    )
    app.dependency_overrides[api_leaderboard.get_suscriptor] = lambda: almacen
    app.dependency_overrides[api_leaderboard.calculador_ranking] = lambda: (
        servicio_leaderboard.ranking
    )

    with TestClient(app) as client:
        yield {
            "client": client,
            "sesion": sesion,
            "repo": repo,
            "respuestas": respuestas,
            "registro": registro,
        }
    app.dependency_overrides.clear()


def _iniciar_y_lanzar(e):
    sid = e["sesion"].id
    for accion in ("iniciar", "lanzar-inject"):
        r = e["client"].post(f"/api/sesiones/{sid}/en-vivo/{accion}", headers=MODERADOR)
        assert r.status_code == 200


def _responder(e):
    _iniciar_y_lanzar(e)
    tarea = e["sesion"].tareas[0]
    r = e["client"].post(
        f"/api/mis-sesiones/{e['sesion'].id}/tareas/{tarea.id}/respuesta",
        json={"opciones": [0]},
        headers=PARTICIPANTE,
    )
    assert r.status_code == 201


# --- REST: reglas de acceso -------------------------------------------------------------


def test_sin_sesion_es_401(e):
    assert e["client"].get("/api/leaderboard/sesiones").status_code == 401
    sid = e["sesion"].id
    assert e["client"].get(f"/api/leaderboard/sesiones/{sid}").status_code == 401


@pytest.mark.parametrize("headers", [PARTICIPANTE, ANALISTA])
def test_sin_permiso_es_403(e, headers):
    assert (
        e["client"].get("/api/leaderboard/sesiones", headers=headers).status_code == 403
    )
    sid = e["sesion"].id
    assert (
        e["client"].get(f"/api/leaderboard/sesiones/{sid}", headers=headers).status_code
        == 403
    )


@pytest.mark.parametrize("estado", [EstadoSesion.BORRADOR, EstadoSesion.PROGRAMADA])
@pytest.mark.parametrize("headers", [MODERADOR, OBSERVADOR, ADMINISTRADOR])
def test_borrador_o_programada_es_404_para_cualquiera(e, estado, headers):
    e["sesion"].estado = estado
    e["repo"].guardar(e["sesion"])
    sid = e["sesion"].id
    assert (
        e["client"].get(f"/api/leaderboard/sesiones/{sid}", headers=headers).status_code
        == 404
    )
    assert e["client"].get("/api/leaderboard/sesiones", headers=headers).json() == []


@pytest.mark.parametrize("headers", [OBSERVADOR, ADMINISTRADOR])
def test_observador_y_administrador_ven_cualquier_sesion_en_curso_o_finalizada(
    e, headers
):
    _iniciar_y_lanzar(e)
    sid = e["sesion"].id
    r = e["client"].get("/api/leaderboard/sesiones", headers=headers)
    assert [s["id"] for s in r.json()] == [str(sid)]
    r = e["client"].get(f"/api/leaderboard/sesiones/{sid}", headers=headers)
    assert r.status_code == 200
    assert r.json()["sesion"]["estado"] == "en_curso"


def test_moderador_ve_su_sesion_pero_otra_es_404(e):
    ajena = _sesion(EstadoSesion.EN_CURSO, moderador_id=uuid4())
    e["repo"].guardar(ajena)
    _iniciar_y_lanzar(e)

    r = e["client"].get("/api/leaderboard/sesiones", headers=MODERADOR)
    assert [s["id"] for s in r.json()] == [str(e["sesion"].id)]
    assert (
        e["client"]
        .get(f"/api/leaderboard/sesiones/{ajena.id}", headers=MODERADOR)
        .status_code
        == 404
    )


def test_sin_sesion_inexistente_es_404(e):
    r = e["client"].get(f"/api/leaderboard/sesiones/{uuid4()}", headers=OBSERVADOR)
    assert r.status_code == 404


# --- La respuesta nunca lleva contenido de las respuestas -------------------------------


def test_el_json_no_expone_texto_opciones_ni_criterios(e):
    _responder(e)
    sid = e["sesion"].id
    r = e["client"].get(f"/api/leaderboard/sesiones/{sid}", headers=OBSERVADOR)
    assert r.status_code == 200
    bruto = r.text
    for prohibido in (
        "Regulador",
        "No paga nunca el rescate",
        "Sí, para recuperar",
        "¿Paga el rescate?",
        "¿A quién notifica?",
    ):
        assert prohibido not in bruto
    [fila] = r.json()["participantes"]
    assert set(fila) == {
        "posicion",
        "usuario_id",
        "nombre",
        "rol_codigo",
        "rol_nombre",
        "puntaje",
        "maximo",
        "porcentaje",
        "respondidas",
        "sin_responder",
    }


# --- WebSocket ---------------------------------------------------------------------------


def _ws_url(sesion_id):
    return f"/api/ws/leaderboard/{sesion_id}"


def test_ws_participante_recibe_4403(e):
    _iniciar_y_lanzar(e)
    url = _ws_url(e["sesion"].id)
    with (
        e["client"].websocket_connect(url, headers=PARTICIPANTE) as ws,
        pytest.raises(Exception),  # noqa: B017 - el servidor cierra antes de enviar nada
    ):
        ws.receive_json()


def test_ws_envia_ranking_al_conectar_y_otra_vez_tras_respuesta_y_ajuste(e):
    _responder(e)
    [fila] = e["registro"].de_sesion(e["sesion"].id, ID_MODERADOR)
    client, sid = e["client"], e["sesion"].id
    with client.websocket_connect(_ws_url(sid), headers=OBSERVADOR) as ws:
        primero = ws.receive_json()
        assert primero["tipo"] == "leaderboard"
        [p] = primero["datos"]["participantes"]
        assert p["puntaje"] == 10  # acertó la opción correcta

        # Otra respuesta (del rol legal, sin participante asignado) no hay;
        # en cambio un ajuste de puntaje sí debe disparar un nuevo envío.
        r = client.post(
            f"/api/sesiones/{sid}/respuestas/{fila.respuesta.id}/ajustes",
            json={"puntaje": 3, "motivo": "Se revisó la justificación a mano"},
            headers=MODERADOR,
        )
        assert r.status_code == 201

        segundo = ws.receive_json()
        assert segundo["tipo"] == "leaderboard"
        [p2] = segundo["datos"]["participantes"]
        assert p2["puntaje"] == 3


def test_ws_cierra_con_1000_al_finalizar(e):
    _responder(e)
    client, sid = e["client"], e["sesion"].id
    with client.websocket_connect(_ws_url(sid), headers=MODERADOR) as ws:
        ws.receive_json()
        client.post(f"/api/sesiones/{sid}/en-vivo/cerrar", headers=MODERADOR)
        final = ws.receive_json()
        assert final["datos"]["sesion"]["estado"] == "finalizada"
        with pytest.raises(Exception):  # noqa: B017 - el socket ya se cerró con 1000
            ws.receive_json()


def test_ws_agrupa_rafagas_en_un_solo_recalculo_por_segundo(e):
    """Diez avisos casi juntos producen un solo recálculo, y llega en ≤ 3 s."""
    _iniciar_y_lanzar(e)
    sid = e["sesion"].id
    servicio_leaderboard = app.dependency_overrides[
        api_leaderboard.get_servicio_leaderboard
    ]()
    llamadas: list[float] = []

    def ranking_contado(sesion_id, usuario_id, es_moderador):
        llamadas.append(time.monotonic())
        return servicio_leaderboard.ranking(sesion_id, usuario_id, es_moderador)

    app.dependency_overrides[api_leaderboard.calculador_ranking] = lambda: (
        ranking_contado
    )
    almacen = app.dependency_overrides[en_vivo.get_suscriptor]()

    with e["client"].websocket_connect(_ws_url(sid), headers=OBSERVADOR) as ws:
        ws.receive_json()  # el envío inicial, al suscribirse
        llamadas.clear()
        inicio = time.monotonic()

        # Diez avisos "seguidos", como si llegaran diez respuestas casi a la vez.
        for _ in range(10):
            almacen.publicar(EventoEnVivo(sid, "respuesta"))

        mensaje = ws.receive_json()
        latencia = time.monotonic() - inicio
        assert mensaje["tipo"] == "leaderboard"
        assert latencia <= 3

    assert len(llamadas) == 1
