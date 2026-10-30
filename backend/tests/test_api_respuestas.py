"""API de tareas y respuestas (PB-08) y registro por sesión (PB-09) con dobles."""

from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import en_vivo, mis_sesiones
from app.adapters.inbound.api import respuestas as api_respuestas
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.application.respuestas import ServicioRegistroRespuestas, ServicioRespuestas
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
ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
ID_PARTICIPANTE = uuid5(NAMESPACE_URL, "prueba:participante")


class CatalogoFalso:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


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
    respuestas = RepoRespuestasEnMemoria()
    servicio = ServicioRespuestas(repo, almacen, respuestas)
    app.dependency_overrides[mis_sesiones.get_servicio_respuestas] = lambda: servicio
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
    registro = ServicioRegistroRespuestas(repo, respuestas, CatalogoFalso(), usuarios)
    app.dependency_overrides[api_respuestas.get_servicio_registro] = lambda: registro
    with TestClient(app) as client:
        yield {"client": client, "sesion": sesion}
    app.dependency_overrides.pop(en_vivo.get_servicio_en_vivo, None)
    app.dependency_overrides.pop(mis_sesiones.get_servicio_respuestas, None)
    app.dependency_overrides.pop(api_respuestas.get_servicio_registro, None)


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


# --- Registro por sesión (PB-09) ------------------------------------------------------


def _registro(e, headers=MODERADOR):
    return e["client"].get(
        f"/api/sesiones/{e['sesion'].id}/respuestas", headers=headers
    )


def test_el_moderador_consulta_las_respuestas_con_toda_su_trazabilidad(e):
    assert _registro(e).json() == []
    _iniciar_y_lanzar(e)
    tarea = e["sesion"].tareas[0]
    e["client"].post(_url(e, tarea), json={"opciones": [1]}, headers=PARTICIPANTE)

    r = _registro(e)
    assert r.status_code == 200
    [fila] = r.json()
    assert fila["participante_id"] == str(ID_PARTICIPANTE)
    assert fila["participante_nombre"] == "Ana López"
    assert fila["rol_codigo"] == "ti" and fila["rol_nombre"] == "Responsable de TI"
    assert fila["inject_orden"] == 1 and fila["inject_titulo"] == "Detección"
    assert fila["tarea_id"] == str(tarea.id)
    assert fila["tarea_enunciado"] == "¿Paga el rescate?"
    assert fila["opciones_elegidas"] == [1]
    assert fila["opciones_elegidas_texto"] == ["Sí"]
    assert fila["recibida_en"] and fila["segundos_usados"] >= 0


def test_registro_solo_para_el_moderador_duenio(e):
    assert _registro(e, headers={}).status_code == 401
    assert _registro(e, headers=PARTICIPANTE).status_code == 403
    r = e["client"].get(f"/api/sesiones/{uuid4()}/respuestas", headers=MODERADOR)
    assert r.status_code == 404


def test_la_api_no_permite_modificar_ni_borrar_respuestas(e):
    _iniciar_y_lanzar(e)
    tarea = e["sesion"].tareas[0]
    url = _url(e, tarea)
    e["client"].post(url, json={"opciones": [0]}, headers=PARTICIPANTE)
    for metodo in ("put", "patch", "delete"):
        r = e["client"].request(
            metodo, url, json={"opciones": [1]}, headers=PARTICIPANTE
        )
        assert r.status_code == 405, metodo
    registro = f"/api/sesiones/{e['sesion'].id}/respuestas"
    assert e["client"].delete(registro, headers=MODERADOR).status_code == 405
    [fila] = _registro(e).json()
    assert fila["opciones_elegidas"] == [0]


# --- Puntaje y ajustes (PB-10) --------------------------------------------------------


def _responder_bien(e):
    _iniciar_y_lanzar(e)
    tarea = e["sesion"].tareas[0]
    r = e["client"].post(_url(e, tarea), json={"opciones": [0]}, headers=PARTICIPANTE)
    assert r.status_code == 201
    [fila] = _registro(e).json()
    return fila


def test_la_respuesta_se_evalua_al_recibirla(e):
    fila = _responder_bien(e)
    assert fila["puntaje_maximo"] == 10
    assert fila["puntaje_automatico"] == fila["puntaje"] == 10
    assert (fila["completitud"], fila["precision"]) == (1, 1)
    assert fila["aciertos"] == ["No"] and fila["errores"] == []
    assert fila["ajustes"] == []


def test_el_participante_no_ve_su_puntaje(e):
    _responder_bien(e)
    [t] = e["client"].get(_url(e), headers=PARTICIPANTE).json()
    assert "puntaje" not in str(t)


def test_ajuste_manual_con_registro_del_cambio(e):
    fila = _responder_bien(e)
    url = f"/api/sesiones/{e['sesion'].id}/respuestas/{fila['id']}/ajustes"

    r = e["client"].post(
        url, json={"puntaje": 7.5, "motivo": "Faltó justificar"}, headers=MODERADOR
    )
    assert r.status_code == 201, r.text
    ajustada = r.json()
    assert ajustada["puntaje"] == 7.5 and ajustada["puntaje_automatico"] == 10
    [a] = ajustada["ajustes"]
    assert (a["puntaje_anterior"], a["puntaje_nuevo"]) == (10, 7.5)
    assert a["motivo"] == "Faltó justificar" and a["creado_en"]

    # Un segundo ajuste parte del vigente y no borra el primero.
    r = e["client"].post(
        url, json={"puntaje": 9, "motivo": "Revisado con el equipo"}, headers=MODERADOR
    )
    assert [x["puntaje_anterior"] for x in r.json()["ajustes"]] == [10, 7.5]
    assert _registro(e).json()[0]["puntaje"] == 9


def test_ajuste_invalido(e):
    fila = _responder_bien(e)
    url = f"/api/sesiones/{e['sesion'].id}/respuestas/{fila['id']}/ajustes"
    r = e["client"].post(url, json={"puntaje": 11, "motivo": "x"}, headers=MODERADOR)
    assert r.status_code == 422
    assert r.json()["detail"]["errores"] == [
        "El puntaje debe estar entre 0 y 10",
        "Explica el motivo del ajuste (al menos 5 caracteres)",
    ]
    otra = f"/api/sesiones/{e['sesion'].id}/respuestas/{uuid4()}/ajustes"
    cuerpo = {"puntaje": 5, "motivo": "Motivo válido"}
    assert e["client"].post(otra, json=cuerpo, headers=MODERADOR).status_code == 404
    assert e["client"].post(url, json=cuerpo, headers=PARTICIPANTE).status_code == 403


def test_puntajes_acumulados_por_participante_y_rol(e):
    _responder_bien(e)
    r = e["client"].get(f"/api/sesiones/{e['sesion'].id}/puntajes", headers=MODERADOR)
    assert r.status_code == 200
    datos = r.json()
    ana, otro = datos["participantes"]
    assert ana["nombre"] == "Ana López" and ana["rol_nombre"] == "Responsable de TI"
    assert (ana["puntaje"], ana["maximo"], ana["porcentaje"]) == (10, 10, 100)
    assert (ana["respondidas"], ana["sin_responder"]) == (1, 0)
    # El participante de Legal no respondió: 0 sobre el máximo de su tarea.
    assert (otro["puntaje"], otro["maximo"], otro["sin_responder"]) == (0, 10, 1)
    roles = {x["rol_codigo"]: x for x in datos["roles"]}
    assert roles["ti"]["puntaje"] == 10 and roles["ti"]["participantes"] == 1
    assert roles["legal"]["porcentaje"] == 0
    otra = f"/api/sesiones/{uuid4()}/puntajes"
    assert e["client"].get(otra, headers=MODERADOR).status_code == 404
