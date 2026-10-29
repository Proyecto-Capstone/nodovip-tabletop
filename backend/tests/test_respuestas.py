"""Tareas por rol y respuestas del participante (PB-08). Sin base de datos."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.application.respuestas import ServicioRespuestas, TareaNoEncontrada
from app.application.sesiones import SesionNoEncontrada
from app.domain.escenarios import Inject, Nivel
from app.domain.respuestas import EstadoTarea
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    ReglaSesionError,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)
from app.ports.respuesta_repository import RespuestaDuplicada
from tests.fakes import RelojFalso, RepoRespuestasEnMemoria, RepoSesionesEnMemoria

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
MODERADOR, ANA, LUIS = uuid4(), uuid4(), uuid4()


def _sesion() -> SesionTabletop:
    i1, i2 = (
        Inject("Detección", "Archivos cifrados", orden=1),
        Inject("Rescate", "Piden 40 BTC", orden=2),
    )
    tareas = [
        TareaSesion(
            "¿Qué sistema aísla primero?",
            "ti",
            Nivel.MEDIO,
            ["Segmenta"],
            inject_id=i1.id,
            tiempo_limite_segundos=120,
        ),
        TareaSesion(
            "¿Paga el rescate?",
            "ti",
            Nivel.ALTO,
            [],
            inject_id=i2.id,
            tipo=TipoTarea.SELECCION_MULTIPLE,
            opciones=[OpcionRespuesta("No", correcta=True), OpcionRespuesta("Sí")],
            tiempo_limite_segundos=60,
        ),
        TareaSesion(
            "¿A quién notifica?", "legal", Nivel.BAJO, ["Regulador"], inject_id=i1.id
        ),
    ]
    return SesionTabletop(
        nombre="Simulacro",
        escenario_id=uuid4(),
        moderador_id=MODERADOR,
        roles=["ti", "legal"],
        injects=[i1, i2],
        tareas=tareas,
        participantes=[
            ParticipanteSesion(ANA, "ti"),
            ParticipanteSesion(LUIS, "legal"),
        ],
        estado=EstadoSesion.PROGRAMADA,
        duracion_minutos=60,
    )


@pytest.fixture
def e():
    repo = RepoSesionesEnMemoria()
    almacen = EnVivoEnMemoria()
    reloj = RelojFalso(T0)
    sesion = repo.guardar(_sesion())
    motor = ServicioEnVivo(repo, almacen, reloj)
    servicio = ServicioRespuestas(repo, almacen, RepoRespuestasEnMemoria(), reloj)
    motor.iniciar(sesion.id, MODERADOR)
    return {"motor": motor, "servicio": servicio, "reloj": reloj, "sesion": sesion}


def _lanzar(e):
    e["motor"].lanzar_inject(e["sesion"].id, MODERADOR)


def _tareas(e, usuario=ANA):
    return e["servicio"].tareas(e["sesion"].id, usuario)


def _responder(e, tarea, texto=None, opciones=(), usuario=ANA):
    return e["servicio"].responder(
        e["sesion"].id, usuario, tarea.id, texto, list(opciones)
    )


# --- Enrutamiento por rol -------------------------------------------------------------


def test_cada_rol_ve_solo_sus_tareas_de_injects_lanzados(e):
    assert _tareas(e) == []  # sesión iniciada, ningún inject lanzado
    _lanzar(e)

    [de_ana] = _tareas(e)
    assert de_ana.tarea.enunciado == "¿Qué sistema aísla primero?"
    [de_luis] = _tareas(e, LUIS)
    assert de_luis.tarea.rol_codigo == "legal"

    _lanzar(e)
    assert [t.inject_orden for t in _tareas(e)] == [2, 1]  # la más reciente primero


def test_no_puede_responder_tareas_de_otro_rol_ni_de_injects_futuros(e):
    _lanzar(e)
    sesion = e["sesion"]
    de_legal = next(t for t in sesion.tareas if t.rol_codigo == "legal")
    del_inject_2 = sesion.tareas[1]
    with pytest.raises(TareaNoEncontrada):
        _responder(e, de_legal, "Al regulador")
    with pytest.raises(TareaNoEncontrada):
        _responder(e, del_inject_2, opciones=[0])


def test_un_usuario_no_invitado_no_ve_la_sesion(e):
    with pytest.raises(SesionNoEncontrada):
        _tareas(e, uuid4())


# --- Tiempo ---------------------------------------------------------------------------


def test_el_tiempo_corre_desde_el_lanzamiento_y_se_detiene_en_pausa(e):
    e["reloj"].avanzar(seconds=30)  # tiempo antes del inject: no cuenta
    _lanzar(e)
    e["reloj"].avanzar(seconds=50)
    assert _tareas(e)[0].segundos_restantes == 70

    e["motor"].pausar(e["sesion"].id, MODERADOR)
    e["reloj"].avanzar(minutes=10)
    assert _tareas(e)[0].segundos_restantes == 70
    with pytest.raises(ReglaSesionError, match="en pausa"):
        _responder(e, _tareas(e)[0].tarea, "Aíslo el file server")

    e["motor"].reanudar(e["sesion"].id, MODERADOR)
    e["reloj"].avanzar(seconds=20)
    assert _tareas(e)[0].segundos_restantes == 50


def test_vencida_no_acepta_respuesta_salvo_la_tolerancia(e):
    _lanzar(e)
    tarea = _tareas(e)[0].tarea
    e["reloj"].avanzar(seconds=121)
    assert _tareas(e)[0].estado == EstadoTarea.VENCIDA
    # 1 s después del límite entra (latencia de red)...
    _responder(e, tarea, "Aíslo el file server")
    assert _tareas(e)[0].estado == EstadoTarea.RESPONDIDA


def test_despues_de_la_tolerancia_se_rechaza(e):
    _lanzar(e)
    tarea = _tareas(e)[0].tarea
    e["reloj"].avanzar(seconds=125)
    with pytest.raises(ReglaSesionError, match="Se agotó el tiempo"):
        _responder(e, tarea, "Tarde")


# --- Una sola respuesta ---------------------------------------------------------------


def test_responde_una_sola_vez_y_queda_registrada(e):
    _lanzar(e)
    tarea = _tareas(e)[0].tarea
    e["reloj"].avanzar(seconds=40)
    r = _responder(e, tarea, "  Aíslo el file server y corto SMB  ")

    assert r.texto == "Aíslo el file server y corto SMB"
    assert r.segundos_usados == 40
    assert r.recibida_en == T0 + timedelta(seconds=40)
    assert r.rol_codigo == "ti" and r.inject_id == tarea.inject_id
    vista = _tareas(e)[0]
    assert vista.estado == EstadoTarea.RESPONDIDA and vista.segundos_restantes == 0
    with pytest.raises(RespuestaDuplicada):
        _responder(e, tarea, "Cambio de opinión")


@pytest.mark.parametrize(
    ("texto", "opciones", "mensaje"),
    [
        (None, [], "Elige al menos una opción"),
        (None, [5], "no existe"),
        (None, [0, 0], "repetidas"),
        ("No pago", [], "eligiendo opciones"),
    ],
)
def test_contenido_de_seleccion_multiple(e, texto, opciones, mensaje):
    _lanzar(e)
    _lanzar(e)
    tarea = next(
        t.tarea for t in _tareas(e) if t.tarea.tipo == TipoTarea.SELECCION_MULTIPLE
    )
    with pytest.raises(ReglaSesionError, match=mensaje):
        _responder(e, tarea, texto, opciones)
    assert _responder(e, tarea, opciones=[0]).opciones_elegidas == [0]


@pytest.mark.parametrize(("texto", "opciones"), [("   ", []), (None, [0])])
def test_contenido_de_texto_libre(e, texto, opciones):
    _lanzar(e)
    with pytest.raises(ReglaSesionError):
        _responder(e, _tareas(e)[0].tarea, texto, opciones)


def test_si_redis_se_pierde_las_tareas_vuelven_a_tener_su_tiempo(e):
    _lanzar(e)
    e["reloj"].avanzar(seconds=100)
    e["motor"].almacen.eliminar(e["sesion"].id)
    assert _tareas(e)[0].segundos_restantes == 120
