"""ServicioMonitoreo (PC-24) con dobles en memoria."""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.monitoreo import ServicioMonitoreo
from app.application.sesiones import SesionNoEncontrada
from app.domain.escenarios import Inject, Nivel, RolEjercicio
from app.domain.evaluacion import evaluar
from app.domain.respuestas import Respuesta
from app.domain.sesiones import (
    EstadoSesion,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
)
from app.domain.usuarios import RolNombre, Usuario
from tests.fakes import (
    RepoRespuestasEnMemoria,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

ID_MODERADOR = uuid4()
ID_P1 = uuid4()
ID_P2 = uuid4()
T0 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


class CatalogoFalso:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


@dataclasses.dataclass
class _EscenarioFalso:
    nombre: str = "Ransomware en sucursal"


class RepoEscenariosFalso:
    def obtener(self, escenario_id):
        return _EscenarioFalso()


def _sesion(
    estado=EstadoSesion.EN_CURSO, *, duracion_minutos=60, iniciada_en=T0
) -> SesionTabletop:
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    return SesionTabletop(
        nombre="Simulacro",
        escenario_id=uuid4(),
        moderador_id=ID_MODERADOR,
        roles=["ti", "legal"],
        injects=[i1],
        tareas=[
            TareaSesion("¿Qué haces?", "ti", Nivel.ALTO, ["Aislar"], inject_id=i1.id),
            TareaSesion(
                "¿A quién avisas?", "legal", Nivel.BAJO, ["Regulador"], inject_id=i1.id
            ),
        ],
        participantes=[
            ParticipanteSesion(ID_P1, "ti"),
            ParticipanteSesion(ID_P2, "legal"),
        ],
        estado=estado,
        inject_actual=1,
        duracion_minutos=duracion_minutos,
        iniciada_en=iniciada_en if estado == EstadoSesion.EN_CURSO else None,
    )


def _servicio(entorno, reloj=lambda: T0, maximo_activas=10) -> ServicioMonitoreo:
    return ServicioMonitoreo(
        entorno["sesiones"],
        entorno["respuestas"],
        CatalogoFalso(),
        entorno["usuarios"],
        RepoEscenariosFalso(),
        entorno["almacen"],
        maximo_activas=maximo_activas,
        reloj=reloj,
    )


@pytest.fixture
def entorno():
    sesiones = RepoSesionesEnMemoria()
    respuestas = RepoRespuestasEnMemoria()
    usuarios = RepoUsuariosEnMemoria()
    almacen = EnVivoEnMemoria()
    usuarios.guardar(
        Usuario(
            "moderadora@demo.test",
            "Mónica Moderadora",
            "hash",
            RolNombre.MODERADOR,
            id=ID_MODERADOR,
        )
    )
    for uid, nombre in [(ID_P1, "Pedro"), (ID_P2, "Ana")]:
        usuarios.guardar(
            Usuario(
                f"{nombre}@demo.test", nombre, "hash", RolNombre.PARTICIPANTE, id=uid
            )
        )
    datos = {
        "sesiones": sesiones,
        "respuestas": respuestas,
        "usuarios": usuarios,
        "almacen": almacen,
    }
    datos["servicio"] = _servicio(datos)
    return datos


def test_resumen_solo_incluye_sesiones_en_curso_y_trae_cupo_y_maximo(entorno):
    sesiones, servicio = entorno["sesiones"], entorno["servicio"]
    en_curso_1 = _sesion(EstadoSesion.EN_CURSO)
    en_curso_2 = _sesion(EstadoSesion.EN_CURSO)
    for s in (
        en_curso_1,
        en_curso_2,
        _sesion(EstadoSesion.PROGRAMADA),
        _sesion(EstadoSesion.FINALIZADA),
        _sesion(EstadoSesion.BORRADOR),
    ):
        sesiones.guardar(s)

    resumen = servicio.resumen()
    assert resumen.maximo == 10
    assert resumen.activas == 2
    assert {f.id for f in resumen.sesiones} == {en_curso_1.id, en_curso_2.id}


def test_fila_trae_moderador_escenario_invitados_conectados_y_avance(entorno):
    sesiones = entorno["sesiones"]
    respuestas = entorno["respuestas"]
    almacen = entorno["almacen"]
    servicio = entorno["servicio"]

    sesion = _sesion(EstadoSesion.EN_CURSO)
    sesiones.guardar(sesion)
    almacen.conectar(sesion.id, ID_P1)

    tarea_ti = next(t for t in sesion.tareas if t.rol_codigo == "ti")
    evaluacion = evaluar(tarea_ti, sesion.pesos, None, [], segundos_usados=0)
    respuestas.guardar(
        Respuesta(
            sesion_id=sesion.id,
            tarea_id=tarea_ti.id,
            inject_id=tarea_ti.inject_id,
            usuario_id=ID_P1,
            rol_codigo="ti",
            recibida_en=T0,
            segundos_usados=0,
            texto=None,
            opciones_elegidas=[],
            evaluacion=evaluacion,
        )
    )

    [fila] = servicio.resumen().sesiones
    assert fila.moderador_nombre == "Mónica Moderadora"
    assert fila.escenario_nombre == "Ransomware en sucursal"
    assert fila.invitados == 2
    assert fila.conectados == 1
    assert fila.respuestas_recibidas == 1
    assert fila.respuestas_esperadas == 2
    assert fila.porcentaje_avance == 50.0
    assert fila.pausada is False
    assert fila.excede_duracion is False


@pytest.mark.parametrize(
    "estado",
    [EstadoSesion.BORRADOR, EstadoSesion.PROGRAMADA, EstadoSesion.FINALIZADA],
)
def test_detalle_404_si_la_sesion_no_esta_en_curso(entorno, estado):
    sesiones, servicio = entorno["sesiones"], entorno["servicio"]
    sesion = _sesion(estado)
    sesiones.guardar(sesion)
    with pytest.raises(SesionNoEncontrada):
        servicio.detalle(sesion.id)


def test_detalle_404_si_la_sesion_no_existe(entorno):
    with pytest.raises(SesionNoEncontrada):
        entorno["servicio"].detalle(uuid4())


def test_detalle_trae_avance_por_participante_y_rol_sin_texto_de_respuestas(entorno):
    sesiones, almacen, servicio = (
        entorno["sesiones"],
        entorno["almacen"],
        entorno["servicio"],
    )
    sesion = _sesion(EstadoSesion.EN_CURSO)
    sesiones.guardar(sesion)
    almacen.conectar(sesion.id, ID_P1)

    detalle = servicio.detalle(sesion.id)
    assert detalle.sesion.id == sesion.id
    assert {p.usuario_id for p in detalle.participantes} == {ID_P1, ID_P2}
    assert {r.rol_codigo for r in detalle.roles} == {"ti", "legal"}
    # Quién está conectado, no solo el conteo (para marcar el punto
    # verde/gris por participante en el panel de lectura).
    assert detalle.conectados_ids == frozenset({ID_P1})

    # Nunca texto de respuestas, opciones elegidas ni criterios de la tarea
    # (mismo principio de mínimo privilegio que el leaderboard, PB-12).
    campos = {f.name for f in dataclasses.fields(detalle.participantes[0])}
    campos |= {f.name for f in dataclasses.fields(detalle.participantes[0].acumulado)}
    assert campos.isdisjoint({"texto", "opciones_elegidas", "criterios", "opciones"})


def test_una_sesion_que_excede_su_duracion_queda_marcada(entorno):
    sesiones = entorno["sesiones"]
    normal = _sesion(EstadoSesion.EN_CURSO, duracion_minutos=300, iniciada_en=T0)
    abandonada = _sesion(EstadoSesion.EN_CURSO, duracion_minutos=10, iniciada_en=T0)
    sesiones.guardar(normal)
    sesiones.guardar(abandonada)

    servicio = _servicio(entorno, reloj=lambda: T0 + timedelta(hours=2))
    por_id = {f.id: f for f in servicio.resumen().sesiones}
    assert por_id[normal.id].excede_duracion is False
    assert por_id[abandonada.id].excede_duracion is True
