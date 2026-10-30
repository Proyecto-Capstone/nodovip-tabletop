"""ServicioLeaderboard (PB-12) con dobles en memoria: reglas de acceso y ranking."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.leaderboard import ServicioLeaderboard
from app.application.respuestas import ServicioRegistroRespuestas
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
ID_OTRO_MODERADOR = uuid4()
ID_OBSERVADOR = uuid4()
ID_P1 = uuid4()
ID_P2 = uuid4()


class CatalogoFalso:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


def _sesion(estado=EstadoSesion.EN_CURSO, moderador_id=ID_MODERADOR, inject_actual=1):
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    return SesionTabletop(
        nombre="Simulacro",
        escenario_id=uuid4(),
        moderador_id=moderador_id,
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
        inject_actual=inject_actual,
    )


@pytest.fixture
def entorno():
    sesiones = RepoSesionesEnMemoria()
    respuestas = RepoRespuestasEnMemoria()
    usuarios = RepoUsuariosEnMemoria()
    for uid, nombre in [(ID_P1, "Pedro"), (ID_P2, "Ana")]:
        usuarios.guardar(
            Usuario(
                f"{nombre}@demo.test", nombre, "hash", RolNombre.PARTICIPANTE, id=uid
            )
        )
    servicio = ServicioLeaderboard(
        sesiones, respuestas, CatalogoFalso(), usuarios, EnVivoEnMemoria()
    )
    return {
        "sesiones": sesiones,
        "respuestas": respuestas,
        "usuarios": usuarios,
        "servicio": servicio,
    }


def test_observador_y_administrador_ven_cualquier_sesion_en_curso_o_finalizada(entorno):
    sesiones, servicio = entorno["sesiones"], entorno["servicio"]
    en_curso = _sesion(EstadoSesion.EN_CURSO)
    finalizada = _sesion(EstadoSesion.FINALIZADA, moderador_id=ID_OTRO_MODERADOR)
    sesiones.guardar(en_curso)
    sesiones.guardar(finalizada)

    visibles = {
        s.id for s in servicio.sesiones_visibles(ID_OBSERVADOR, es_moderador=False)
    }
    assert visibles == {en_curso.id, finalizada.id}

    # Y puede pedir el ranking de cualquiera de las dos.
    servicio.ranking(en_curso.id, ID_OBSERVADOR, es_moderador=False)
    servicio.ranking(finalizada.id, ID_OBSERVADOR, es_moderador=False)


def test_moderador_solo_ve_sus_sesiones_otra_es_404(entorno):
    sesiones, servicio = entorno["sesiones"], entorno["servicio"]
    propia = _sesion(EstadoSesion.EN_CURSO, moderador_id=ID_MODERADOR)
    ajena = _sesion(EstadoSesion.EN_CURSO, moderador_id=ID_OTRO_MODERADOR)
    sesiones.guardar(propia)
    sesiones.guardar(ajena)

    visibles = {
        s.id for s in servicio.sesiones_visibles(ID_MODERADOR, es_moderador=True)
    }
    assert visibles == {propia.id}

    servicio.ranking(propia.id, ID_MODERADOR, es_moderador=True)
    with pytest.raises(SesionNoEncontrada):
        servicio.ranking(ajena.id, ID_MODERADOR, es_moderador=True)


@pytest.mark.parametrize("estado", [EstadoSesion.BORRADOR, EstadoSesion.PROGRAMADA])
def test_borrador_o_programada_no_es_visible_para_nadie(entorno, estado):
    sesiones, servicio = entorno["sesiones"], entorno["servicio"]
    sesion = _sesion(estado, inject_actual=0)
    sesiones.guardar(sesion)

    assert servicio.sesiones_visibles(ID_OBSERVADOR, es_moderador=False) == []
    assert servicio.sesiones_visibles(ID_MODERADOR, es_moderador=True) == []
    with pytest.raises(SesionNoEncontrada):
        servicio.ranking(sesion.id, ID_OBSERVADOR, es_moderador=False)
    with pytest.raises(SesionNoEncontrada):
        servicio.ranking(sesion.id, ID_MODERADOR, es_moderador=True)


def test_sin_sesion_es_404(entorno):
    with pytest.raises(SesionNoEncontrada):
        entorno["servicio"].ranking(uuid4(), ID_OBSERVADOR, es_moderador=False)


def test_empates_comparten_posicion(entorno):
    sesiones, servicio = entorno["sesiones"], entorno["servicio"]
    sesion = _sesion(EstadoSesion.EN_CURSO)
    sesiones.guardar(sesion)
    # Ninguno respondió: ambos quedan en 0 puntos sobre el mismo máximo (empate).
    ranking = servicio.ranking(sesion.id, ID_OBSERVADOR, es_moderador=False)
    assert [p.posicion for p in ranking.participantes] == [1, 1]
    assert {p.acumulado.puntaje for p in ranking.participantes} == {0}


def test_un_ajuste_cambia_el_ranking(entorno):
    sesiones = entorno["sesiones"]
    respuestas = entorno["respuestas"]
    usuarios = entorno["usuarios"]
    servicio = entorno["servicio"]

    sesion = _sesion(EstadoSesion.EN_CURSO)
    sesiones.guardar(sesion)
    tarea = next(t for t in sesion.tareas if t.rol_codigo == "ti")
    evaluacion = evaluar(tarea, sesion.pesos, None, [], segundos_usados=0)
    respuestas.guardar(
        Respuesta(
            sesion_id=sesion.id,
            tarea_id=tarea.id,
            inject_id=tarea.inject_id,
            usuario_id=ID_P1,
            rol_codigo="ti",
            recibida_en=datetime.now(UTC),
            segundos_usados=0,
            texto=None,
            opciones_elegidas=[],
            evaluacion=evaluacion,
        )
    )
    antes = servicio.ranking(sesion.id, ID_OBSERVADOR, es_moderador=False)
    puntaje_antes = next(
        p.acumulado.puntaje for p in antes.participantes if p.usuario_id == ID_P1
    )
    assert puntaje_antes == 0  # Sin texto: 0 puntos.

    registro = ServicioRegistroRespuestas(
        sesiones, respuestas, CatalogoFalso(), usuarios, EnVivoEnMemoria()
    )
    respuesta = respuestas.de_sesion(sesion.id)[0]
    registro.ajustar(
        sesion.id, ID_MODERADOR, respuesta.id, 8.0, "Respuesta verbal correcta"
    )

    despues = servicio.ranking(sesion.id, ID_OBSERVADOR, es_moderador=False)
    puntaje_despues = next(
        p.acumulado.puntaje for p in despues.participantes if p.usuario_id == ID_P1
    )
    assert puntaje_despues == 8.0
    assert puntaje_despues != puntaje_antes
