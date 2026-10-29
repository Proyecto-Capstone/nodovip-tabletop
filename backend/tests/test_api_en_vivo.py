"""Motor en tiempo real (PB-07): comandos REST y WebSocket con estado en memoria."""

import time
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.adapters.inbound.api import en_vivo
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.domain.escenarios import Escenario, EstadoEscenario, Inject, Nivel, Tarea
from app.domain.sesiones import EstadoSesion, ParticipanteSesion, SesionTabletop
from app.main import app
from tests.fakes import RepoSesionesEnMemoria

MODERADOR = {"X-Rol-Prueba": "moderador"}
PARTICIPANTE = {"X-Rol-Prueba": "participante"}
OBSERVADOR = {"X-Rol-Prueba": "observador"}
ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
ID_PARTICIPANTE = uuid5(NAMESPACE_URL, "prueba:participante")


def _sesion(moderador=ID_MODERADOR, participante=ID_PARTICIPANTE) -> SesionTabletop:
    escenario = Escenario(
        "Ransomware en sucursal",
        "ransomware",
        "Cifrado de servidores",
        Nivel.ALTO,
        ["ti"],
        injects=[
            Inject("Detección inicial", "TI detecta archivos cifrados", orden=1),
            Inject("Nota de rescate", "Piden 40 BTC en 72 horas", orden=2),
        ],
        tareas=[Tarea("¿Qué aísla primero?", "ti", Nivel.MEDIO, ["Segmenta"])],
        estado=EstadoEscenario.PUBLICADO,
    )
    sesion = SesionTabletop.desde_escenario(escenario, moderador, "Simulacro Q4")
    sesion.participantes = [ParticipanteSesion(participante, "ti")]
    sesion.fecha_programada = datetime.now(UTC) + timedelta(days=1)
    sesion.duracion_minutos = 60
    sesion.estado = EstadoSesion.PROGRAMADA
    return sesion


@pytest.fixture
def entorno(sesion_por_cabecera):
    repo = RepoSesionesEnMemoria()
    almacen = EnVivoEnMemoria()
    sesion = repo.guardar(_sesion())
    app.dependency_overrides[en_vivo.get_servicio_en_vivo] = lambda: ServicioEnVivo(
        repo, almacen
    )
    app.dependency_overrides[en_vivo.get_suscriptor] = lambda: almacen
    # Un solo cliente (y un solo event loop) para REST y WebSocket.
    with TestClient(app) as client:
        yield {"client": client, "repo": repo, "almacen": almacen, "sesion": sesion}
    app.dependency_overrides.pop(en_vivo.get_servicio_en_vivo, None)
    app.dependency_overrides.pop(en_vivo.get_suscriptor, None)


def _url(e, accion=""):
    base = f"/api/sesiones/{e['sesion'].id}/en-vivo"
    return f"{base}/{accion}" if accion else base


def _ws(e):
    return f"/api/ws/sesiones/{e['sesion'].id}"


def _comando(e, accion, cabecera=MODERADOR, esperado=200):
    r = e["client"].post(_url(e, accion), headers=cabecera)
    assert r.status_code == esperado, r.text
    return r.json()


def _recibir_hasta(ws, condicion, maximo=5):
    """Lee mensajes hasta que uno cumple la condición (los de presencia se saltan)."""
    for _ in range(maximo):
        vista = ws.receive_json()["vista"]
        if condicion(vista):
            return vista
    raise AssertionError("No llegó el mensaje esperado")


# --- Comandos REST --------------------------------------------------------------------


def test_ciclo_completo_del_moderador(entorno):
    v = _comando(entorno, "iniciar")
    assert v["estado"] == "en_curso" and v["inject_actual"] == 0 and v["inject"] is None

    v = _comando(entorno, "lanzar-inject")
    assert v["inject_actual"] == 1 and v["inject"]["titulo"] == "Detección inicial"

    assert _comando(entorno, "pausar")["pausada"] is True
    assert _comando(entorno, "reanudar")["pausada"] is False

    v = _comando(entorno, "cerrar")
    assert v["estado"] == "finalizada"
    guardada = entorno["repo"].obtener(entorno["sesion"].id)
    assert guardada.estado == EstadoSesion.FINALIZADA
    assert guardada.finalizada_en is not None and guardada.inject_actual == 1
    # Al cerrar se libera el estado en Redis.
    assert entorno["almacen"].obtener(entorno["sesion"].id) is None


def test_el_participante_no_puede_conducir(entorno):
    for accion in ("iniciar", "lanzar-inject", "pausar", "cerrar"):
        _comando(entorno, accion, PARTICIPANTE, 403)


def test_un_moderador_no_conduce_sesiones_ajenas(entorno):
    ajena = entorno["repo"].guardar(_sesion(moderador=uuid4()))
    r = entorno["client"].post(
        f"/api/sesiones/{ajena.id}/en-vivo/iniciar", headers=MODERADOR
    )
    assert r.status_code == 404


def test_reglas_del_motor_responden_422(entorno):
    _comando(entorno, "lanzar-inject", esperado=422)  # todavía no inició
    _comando(entorno, "iniciar")
    _comando(entorno, "iniciar", esperado=422)  # ya en curso
    _comando(entorno, "lanzar-inject")
    _comando(entorno, "lanzar-inject")
    errores = _comando(entorno, "lanzar-inject", esperado=422)["detail"]["errores"]
    assert errores == ["Ya se lanzaron todos los injects"]


def test_si_redis_pierde_el_estado_se_reconstruye_desde_postgresql(entorno):
    _comando(entorno, "iniciar")
    _comando(entorno, "lanzar-inject")
    entorno["almacen"].eliminar(entorno["sesion"].id)  # se "cae" Redis

    v = entorno["client"].get(_url(entorno), headers=MODERADOR).json()
    assert v["estado"] == "en_curso" and v["inject_actual"] == 1
    assert _comando(entorno, "lanzar-inject")["inject_actual"] == 2


# --- WebSocket ------------------------------------------------------------------------


def test_websocket_rechaza_sin_sesion_sin_permiso_o_sin_invitacion(entorno):
    client = entorno["client"]
    for cabecera, codigo in [({}, 4401), (OBSERVADOR, 4403)]:
        with (
            pytest.raises(WebSocketDisconnect) as e,
            client.websocket_connect(_ws(entorno), headers=cabecera) as ws,
        ):
            ws.receive_json()
        assert e.value.code == codigo

    ajena = entorno["repo"].guardar(_sesion(participante=uuid4()))
    with (
        pytest.raises(WebSocketDisconnect) as e,
        client.websocket_connect(
            f"/api/ws/sesiones/{ajena.id}", headers=PARTICIPANTE
        ) as ws,
    ):
        ws.receive_json()
    assert e.value.code == 4404


def test_el_participante_recibe_cada_cambio_en_menos_de_3_segundos(entorno):
    client = entorno["client"]
    with client.websocket_connect(_ws(entorno), headers=PARTICIPANTE) as ws:
        inicial = ws.receive_json()["vista"]
        assert inicial["estado"] == "programada"
        assert inicial["conectados"] is None  # el participante no ve quiénes

        _comando(entorno, "iniciar")
        assert (
            _recibir_hasta(ws, lambda v: v["estado"] == "en_curso")["inject_actual"]
            == 0
        )

        inicio = time.monotonic()
        _comando(entorno, "lanzar-inject")
        v = _recibir_hasta(ws, lambda v: v["inject_actual"] == 1)
        assert time.monotonic() - inicio < 3
        assert v["inject"]["descripcion"] == "TI detecta archivos cifrados"

        _comando(entorno, "pausar")
        assert _recibir_hasta(ws, lambda v: v["pausada"])["pausada"]


def test_al_reconectarse_recupera_el_estado_actual(entorno):
    client = entorno["client"]
    _comando(entorno, "iniciar")
    with client.websocket_connect(_ws(entorno), headers=PARTICIPANTE) as ws:
        ws.receive_json()
    # Mientras estaba desconectado, el moderador avanzó.
    _comando(entorno, "lanzar-inject")
    _comando(entorno, "lanzar-inject")

    with client.websocket_connect(_ws(entorno), headers=PARTICIPANTE) as ws:
        v = ws.receive_json()["vista"]
        assert v["estado"] == "en_curso" and v["inject_actual"] == 2
        assert v["inject"]["titulo"] == "Nota de rescate"


def test_el_moderador_ve_quien_esta_conectado(entorno):
    client = entorno["client"]
    with client.websocket_connect(_ws(entorno), headers=MODERADOR) as mod:
        assert mod.receive_json()["vista"]["conectados"] == [str(ID_MODERADOR)]
        with client.websocket_connect(_ws(entorno), headers=PARTICIPANTE) as par:
            par.receive_json()
            v = _recibir_hasta(mod, lambda v: len(v["conectados"]) == 2)
            assert str(ID_PARTICIPANTE) in v["conectados"]
        v = _recibir_hasta(mod, lambda v: len(v["conectados"]) == 1)
        assert v["total_conectados"] == 1


def test_al_cerrar_el_participante_recibe_el_fin_y_se_cierra_el_socket(entorno):
    client = entorno["client"]
    _comando(entorno, "iniciar")
    with client.websocket_connect(_ws(entorno), headers=PARTICIPANTE) as ws:
        ws.receive_json()
        _comando(entorno, "cerrar")
        assert _recibir_hasta(ws, lambda v: v["estado"] == "finalizada")
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 1000
