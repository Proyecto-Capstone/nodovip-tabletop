"""API y WebSocket del monitoreo de sesiones activas (PC-24) con dobles en memoria."""

from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.adapters.inbound.api import en_vivo
from app.adapters.inbound.api import monitoreo as api_monitoreo
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.application.monitoreo import ServicioMonitoreo
from app.domain.escenarios import Inject, Nivel, RolEjercicio
from app.domain.sesiones import (
    EstadoSesion,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
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
        return [RolEjercicio("ti", "Responsable de TI")]


class _EscenarioFalso:
    nombre = "Ransomware en sucursal"


class RepoEscenariosFalso:
    def obtener(self, escenario_id):
        return _EscenarioFalso()


def _sesion(estado=EstadoSesion.PROGRAMADA) -> SesionTabletop:
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    return SesionTabletop(
        nombre="Simulacro",
        escenario_id=uuid4(),
        moderador_id=ID_MODERADOR,
        roles=["ti"],
        injects=[i1],
        tareas=[
            TareaSesion("¿Qué haces?", "ti", Nivel.ALTO, ["Aislar"], inject_id=i1.id)
        ],
        participantes=[ParticipanteSesion(ID_PARTICIPANTE, "ti")],
        estado=estado,
        duracion_minutos=60,
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
    usuarios = RepoUsuariosEnMemoria()
    usuarios.guardar(
        Usuario(
            "moderador@prueba.test",
            "Prueba moderador",
            "hash",
            RolNombre.MODERADOR,
            id=ID_MODERADOR,
        )
    )
    servicio_monitoreo = ServicioMonitoreo(
        repo,
        respuestas,
        CatalogoFalso(),
        usuarios,
        RepoEscenariosFalso(),
        almacen,
        maximo_activas=10,
    )
    app.dependency_overrides[api_monitoreo.get_servicio_monitoreo] = lambda: (
        servicio_monitoreo
    )
    app.dependency_overrides[api_monitoreo.get_suscriptor] = lambda: almacen
    app.dependency_overrides[api_monitoreo.calculador_detalle] = lambda: (
        servicio_monitoreo.detalle
    )

    with TestClient(app) as client:
        yield {
            "client": client,
            "sesion": sesion,
            "repo": repo,
            "almacen": almacen,
        }
    app.dependency_overrides.clear()


def _iniciar(e):
    sid = e["sesion"].id
    r = e["client"].post(f"/api/sesiones/{sid}/en-vivo/iniciar", headers=MODERADOR)
    assert r.status_code == 200
    return r


def _ws(sesion_id):
    return f"/api/ws/monitoreo/{sesion_id}"


# --- REST: reglas de acceso ----------------------------------------------------------


def test_sin_sesion_es_401(e):
    assert e["client"].get("/api/monitoreo/sesiones").status_code == 401
    sid = e["sesion"].id
    assert e["client"].get(f"/api/monitoreo/sesiones/{sid}").status_code == 401


@pytest.mark.parametrize("headers", [MODERADOR, PARTICIPANTE, OBSERVADOR, ANALISTA])
def test_sin_permiso_es_403(e, headers):
    assert (
        e["client"].get("/api/monitoreo/sesiones", headers=headers).status_code == 403
    )
    sid = e["sesion"].id
    assert (
        e["client"].get(f"/api/monitoreo/sesiones/{sid}", headers=headers).status_code
        == 403
    )


# --- REST: resumen y detalle -----------------------------------------------------------


def test_sesion_programada_no_aparece_hasta_que_se_inicia(e):
    r = e["client"].get("/api/monitoreo/sesiones", headers=ADMINISTRADOR)
    assert r.status_code == 200
    assert r.json() == {"activas": 0, "maximo": 10, "sesiones": []}

    _iniciar(e)
    r = e["client"].get("/api/monitoreo/sesiones", headers=ADMINISTRADOR).json()
    assert r["activas"] == 1 and r["maximo"] == 10
    [fila] = r["sesiones"]
    assert fila["id"] == str(e["sesion"].id)
    assert fila["moderador_nombre"] == "Prueba moderador"
    assert fila["escenario_nombre"] == "Ransomware en sucursal"
    assert fila["invitados"] == 1
    assert fila["conectados"] == 0
    assert fila["pausada"] is False
    assert fila["excede_duracion"] is False


def test_detalle_de_una_sesion_en_curso(e):
    _iniciar(e)
    sid = e["sesion"].id
    e["almacen"].conectar(sid, ID_PARTICIPANTE)
    r = e["client"].get(f"/api/monitoreo/sesiones/{sid}", headers=ADMINISTRADOR)
    assert r.status_code == 200
    body = r.json()
    assert body["sesion"]["id"] == str(sid)
    assert {p["usuario_id"] for p in body["participantes"]} == {str(ID_PARTICIPANTE)}
    assert {rol["rol_codigo"] for rol in body["roles"]} == {"ti"}
    assert body["conectados_ids"] == [str(ID_PARTICIPANTE)]
    # Nunca texto de respuestas, opciones elegidas ni criterios (mismo
    # principio de mínimo privilegio que el leaderboard, PB-12).
    [p] = body["participantes"]
    assert set(p) == {
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


@pytest.mark.parametrize(
    "estado", [EstadoSesion.BORRADOR, EstadoSesion.PROGRAMADA, EstadoSesion.FINALIZADA]
)
def test_detalle_404_si_la_sesion_no_esta_en_curso(e, estado):
    e["sesion"].estado = estado
    e["repo"].guardar(e["sesion"])
    sid = e["sesion"].id
    r = e["client"].get(f"/api/monitoreo/sesiones/{sid}", headers=ADMINISTRADOR)
    assert r.status_code == 404


def test_detalle_404_si_la_sesion_no_existe(e):
    r = e["client"].get(f"/api/monitoreo/sesiones/{uuid4()}", headers=ADMINISTRADOR)
    assert r.status_code == 404


# --- WebSocket -----------------------------------------------------------------------


def test_websocket_rechaza_sin_sesion_sin_permiso_o_si_no_esta_en_curso(e):
    client = e["client"]
    sid = e["sesion"].id
    for cabecera, codigo in [({}, 4401), (MODERADOR, 4403), (PARTICIPANTE, 4403)]:
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(_ws(sid), headers=cabecera) as ws,
        ):
            ws.receive_json()
        assert exc.value.code == codigo

    # Todavía PROGRAMADA: el permiso alcanza, pero no hay nada que monitorear.
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        client.websocket_connect(_ws(sid), headers=ADMINISTRADOR) as ws,
    ):
        ws.receive_json()
    assert exc.value.code == 4404


def test_websocket_envia_el_detalle_y_no_registra_al_administrador_como_conectado(e):
    _iniciar(e)
    client, sid = e["client"], e["sesion"].id
    with client.websocket_connect(_ws(sid), headers=ADMINISTRADOR) as ws:
        primero = ws.receive_json()
        assert primero["tipo"] == "monitoreo"
        assert primero["datos"]["sesion"]["id"] == str(sid)

        # El moderador, mirando su propia sesión, no ve al admin conectado.
        vista = client.get(f"/api/sesiones/{sid}/en-vivo", headers=MODERADOR).json()
        assert vista["total_conectados"] == 0

        # Tampoco el resumen de monitoreo lo cuenta.
        resumen = client.get("/api/monitoreo/sesiones", headers=ADMINISTRADOR).json()
        assert resumen["sesiones"][0]["conectados"] == 0
