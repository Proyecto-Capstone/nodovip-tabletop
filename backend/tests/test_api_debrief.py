"""API del debrief y del resumen del participante (PC-45), con dobles en memoria."""

from datetime import UTC, date, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import debrief, reportes
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.debrief import ServicioDebrief, ServicioResumenParticipante
from app.application.reportes import ServicioReportes
from app.domain.escenarios import Inject, Nivel, RolEjercicio
from app.domain.evaluacion import AjustePuntaje
from app.domain.respuestas import Respuesta
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)
from app.main import app
from tests.fakes import (
    GeneradorPdfFalso,
    RepoDebriefEnMemoria,
    RepoReportesEnMemoria,
    RepoRespuestasEnMemoria,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
ID_PARTICIPANTE = uuid5(NAMESPACE_URL, "prueba:participante")
T0 = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
PLAZO = (date.today() + timedelta(days=30)).isoformat()


class CatalogoFalso:
    def roles_ejercicio(self):
        return [
            RolEjercicio("ti", "Responsable de TI"),
            RolEjercicio("legal", "Legal"),
        ]


class EscenariosFalsos:
    def obtener(self, escenario_id):
        return None


def _sesion(estado=EstadoSesion.FINALIZADA, moderador=ID_MODERADOR, inject_actual=2):
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    i2 = Inject("Rescate", "Piden 40 BTC", orden=2)
    i3 = Inject("Prensa", "Llama un periodista", orden=3)
    return SesionTabletop(
        nombre="Simulacro Q4",
        cliente="Banco Andino",
        escenario_id=uuid4(),
        moderador_id=moderador,
        roles=["ti", "legal"],
        injects=[i1, i2, i3],
        tareas=[
            TareaSesion(
                "¿Qué aísla primero?",
                "ti",
                Nivel.ALTO,
                ["aislar la red"],
                inject_id=i1.id,
            ),
            TareaSesion(
                "¿Pagan el rescate?",
                "ti",
                Nivel.MEDIO,
                [],
                inject_id=i2.id,
                tipo=TipoTarea.SELECCION_MULTIPLE,
                opciones=[
                    OpcionRespuesta("No pagar y restaurar", correcta=True),
                    OpcionRespuesta("Pagar de inmediato"),
                ],
            ),
            # Su inject nunca se lanzó: no aparece en el resumen.
            TareaSesion(
                "¿Qué dice a la prensa?",
                "ti",
                Nivel.BAJO,
                ["no confirmar"],
                inject_id=i3.id,
            ),
            TareaSesion(
                "¿A quién notifica?",
                "legal",
                Nivel.ALTO,
                ["autoridad"],
                inject_id=i1.id,
            ),
        ],
        participantes=[
            ParticipanteSesion(ID_PARTICIPANTE, "ti"),
            ParticipanteSesion(uuid4(), "legal"),
        ],
        estado=estado,
        iniciada_en=T0,
        finalizada_en=T0 + timedelta(minutes=40)
        if estado == EstadoSesion.FINALIZADA
        else None,
        inject_actual=inject_actual,
    )


@pytest.fixture
def e(sesion_por_cabecera):
    sesiones, respuestas = RepoSesionesEnMemoria(), RepoRespuestasEnMemoria()
    debriefs, almacen = RepoDebriefEnMemoria(), EnVivoEnMemoria()
    catalogo, usuarios = CatalogoFalso(), RepoUsuariosEnMemoria()
    app.dependency_overrides[debrief.get_servicio_debrief] = lambda: ServicioDebrief(
        sesiones, debriefs, catalogo
    )
    app.dependency_overrides[debrief.get_servicio_resumen] = lambda: (
        ServicioResumenParticipante(
            sesiones, respuestas, catalogo, usuarios, almacen, debriefs
        )
    )
    app.dependency_overrides[reportes.get_servicio_reportes] = lambda: ServicioReportes(
        sesiones,
        respuestas,
        catalogo,
        usuarios,
        EscenariosFalsos(),
        almacen,
        RepoReportesEnMemoria(),
        GeneradorPdfFalso(),
        debriefs=debriefs,
    )
    with TestClient(app) as client:
        yield {"client": client, "sesiones": sesiones, "respuestas": respuestas}
    for dep in (
        debrief.get_servicio_debrief,
        debrief.get_servicio_resumen,
        reportes.get_servicio_reportes,
    ):
        app.dependency_overrides.pop(dep, None)


def _como(rol):
    return {"X-Rol-Prueba": rol}


def _url(sesion, accion=""):
    base = f"/api/sesiones/{sesion.id}/debrief"
    return f"{base}/{accion}" if accion else base


BORRADOR = {
    "fortalezas": ["El CISO escaló en menos de 5 minutos", "  "],
    "mejoras": ["Nadie verificó la copia fuera de línea"],
    "acciones": [
        {
            "descripcion": "Probar la restauración de respaldos cada mes",
            "prioridad": "alta",
            "rol_codigo": "ti",
            "plazo": PLAZO,
        },
        {"descripcion": "Actualizar el plan de comunicación", "prioridad": "media"},
    ],
}


def test_sin_iniciar_devuelve_listas_vacias_y_los_roles(e):
    s = e["sesiones"].guardar(_sesion())
    r = e["client"].get(_url(s), headers=_como("moderador"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estado"] == "sin_iniciar" and d["puede_editar"] is True
    assert d["fortalezas"] == [] and d["acciones"] == []
    assert d["roles"] == [
        {"codigo": "ti", "nombre": "Responsable de TI"},
        {"codigo": "legal", "nombre": "Legal"},
    ]


def test_ciclo_borrador_completar_y_reabrir(e):
    s = e["sesiones"].guardar(_sesion())
    r = e["client"].put(_url(s), json=BORRADOR, headers=_como("moderador"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estado"] == "borrador"
    assert d["fortalezas"] == ["El CISO escaló en menos de 5 minutos"]
    assert d["acciones"][0]["responsable"] == "Responsable de TI"
    assert d["acciones"][1]["responsable"] == "Toda la organización"

    # La segunda acción no tiene plazo: no se puede completar.
    r = e["client"].post(_url(s, "completar"), headers=_como("moderador"))
    assert r.status_code == 422
    assert r.json()["detail"]["errores"] == ["Acción 2: indica un plazo"]

    BORRADOR_OK = {
        **BORRADOR,
        "acciones": [{**a, "plazo": PLAZO} for a in BORRADOR["acciones"]],
    }
    e["client"].put(_url(s), json=BORRADOR_OK, headers=_como("moderador"))
    r = e["client"].post(_url(s, "completar"), headers=_como("moderador"))
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "completado" and r.json()["completado_en"]

    # Completado: no se edita hasta reabrirlo.
    r = e["client"].put(_url(s), json=BORRADOR_OK, headers=_como("moderador"))
    assert r.status_code == 422
    r = e["client"].post(_url(s, "reabrir"), headers=_como("moderador"))
    assert r.json()["estado"] == "borrador"


def test_las_lecciones_llegan_al_reporte_solo_al_completar(e):
    s = e["sesiones"].guardar(_sesion())
    acciones = [{**a, "plazo": PLAZO} for a in BORRADOR["acciones"]]
    e["client"].put(
        _url(s), json={**BORRADOR, "acciones": acciones}, headers=_como("moderador")
    )
    reporte = e["client"].get(f"/api/reportes/{s.id}", headers=_como("analista")).json()
    assert reporte["lecciones"] is None

    e["client"].post(_url(s, "completar"), headers=_como("moderador"))
    lecciones = (
        e["client"]
        .get(f"/api/reportes/{s.id}", headers=_como("analista"))
        .json()["lecciones"]
    )
    assert lecciones["mejoras"] == ["Nadie verificó la copia fuera de línea"]
    assert lecciones["acciones"][0] == {
        "descripcion": "Probar la restauración de respaldos cada mes",
        "responsable": "Responsable de TI",
        "prioridad": "alta",
        "plazo": PLAZO,
    }


@pytest.mark.parametrize("rol", ["analista", "administrador"])
def test_analista_y_administrador_lo_ven_pero_no_lo_editan(e, rol):
    s = e["sesiones"].guardar(_sesion())
    r = e["client"].get(_url(s), headers=_como(rol))
    assert r.status_code == 200 and r.json()["puede_editar"] is False
    assert (
        e["client"].put(_url(s), json=BORRADOR, headers=_como(rol)).status_code == 403
    )
    assert e["client"].post(_url(s, "completar"), headers=_como(rol)).status_code == 403


def test_participante_y_observador_no_acceden_al_debrief(e):
    s = e["sesiones"].guardar(_sesion())
    for rol in ("participante", "observador"):
        assert e["client"].get(_url(s), headers=_como(rol)).status_code == 403
    assert e["client"].get(_url(s)).status_code == 401


def test_moderador_ajeno_o_sesion_sin_finalizar_es_404(e):
    ajena = e["sesiones"].guardar(_sesion(moderador=uuid4()))
    en_curso = e["sesiones"].guardar(_sesion(estado=EstadoSesion.EN_CURSO))
    for s in (ajena, en_curso):
        assert e["client"].get(_url(s), headers=_como("moderador")).status_code == 404
        r = e["client"].put(_url(s), json=BORRADOR, headers=_como("moderador"))
        assert r.status_code == 404


# --- Resumen del participante ---------------------------------------------------------


def _responder(e, s, tarea, **campos):
    e["respuestas"].guardar(
        Respuesta(
            sesion_id=s.id,
            tarea_id=tarea.id,
            inject_id=tarea.inject_id,
            usuario_id=ID_PARTICIPANTE,
            rol_codigo="ti",
            recibida_en=T0 + timedelta(minutes=5),
            segundos_usados=60,
            **campos,
        )
    )


def test_resumen_del_participante_con_retroalimentacion(e):
    s = e["sesiones"].guardar(_sesion())
    texto_libre, seleccion = s.tareas[0], s.tareas[1]
    _responder(e, s, texto_libre, texto="Hay que aislar la red de inmediato")
    _responder(e, s, seleccion, opciones_elegidas=[1])
    respuesta_id = e["respuestas"].de_sesion(s.id)[1].id
    e["respuestas"].agregar_ajuste(
        AjustePuntaje(
            respuesta_id, ID_MODERADOR, 0, 2, "Justificó bien la decisión", T0
        ),
        s.id,
    )

    r = e["client"].get(
        f"/api/mis-sesiones/{s.id}/resumen", headers=_como("participante")
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["rol_nombre"] == "Responsable de TI"
    assert d["posicion"] == 1 and d["total_participantes"] == 2
    # La tarea del inject 3 (no lanzado) no aparece; la de Legal tampoco.
    assert [t["inject_orden"] for t in d["tareas"]] == [1, 2]
    primera, segunda = d["tareas"]
    assert primera["respondida"] and primera["aciertos"] == ["aislar la red"]
    assert segunda["respuesta"] == "Pagar de inmediato"
    assert segunda["opciones_correctas"] == ["No pagar y restaurar"]
    assert segunda["puntaje"] == 2
    assert segunda["ajuste_motivo"] == "Justificó bien la decisión"
    assert d["lecciones"] is None


def test_resumen_muestra_las_tareas_sin_responder_y_las_lecciones_completadas(e):
    s = e["sesiones"].guardar(_sesion())
    acciones = [{**a, "plazo": PLAZO} for a in BORRADOR["acciones"]]
    e["client"].put(
        _url(s), json={**BORRADOR, "acciones": acciones}, headers=_como("moderador")
    )
    e["client"].post(_url(s, "completar"), headers=_como("moderador"))

    d = (
        e["client"]
        .get(f"/api/mis-sesiones/{s.id}/resumen", headers=_como("participante"))
        .json()
    )
    sin_responder = d["tareas"][0]
    assert sin_responder["respondida"] is False and sin_responder["puntaje"] == 0
    assert sin_responder["faltantes"] == ["aislar la red"]
    assert d["lecciones"]["fortalezas"] == ["El CISO escaló en menos de 5 minutos"]


def test_resumen_solo_para_invitados_y_sesiones_finalizadas(e):
    en_curso = e["sesiones"].guardar(_sesion(estado=EstadoSesion.EN_CURSO))
    sin_mi = _sesion()
    sin_mi.participantes = [ParticipanteSesion(uuid4(), "ti")]
    e["sesiones"].guardar(sin_mi)
    for s in (en_curso, sin_mi):
        r = e["client"].get(
            f"/api/mis-sesiones/{s.id}/resumen", headers=_como("participante")
        )
        assert r.status_code == 404
    finalizada = e["sesiones"].guardar(_sesion())
    r = e["client"].get(
        f"/api/mis-sesiones/{finalizada.id}/resumen", headers=_como("moderador")
    )
    assert r.status_code == 403
