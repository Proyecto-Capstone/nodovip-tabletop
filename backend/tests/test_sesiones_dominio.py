"""Reglas de negocio de las sesiones tabletop (RF-01, PB-05). Sin base de datos."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    Tarea,
)
from app.domain.sesiones import (
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    PesosPuntuacion,
    ReglaSesionError,
    SesionTabletop,
    TipoTarea,
)

AHORA = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
MODERADOR = uuid4()


def _escenario(estado=EstadoEscenario.PUBLICADO) -> Escenario:
    return Escenario(
        nombre="Ransomware en sucursal",
        tipo_codigo="ransomware",
        descripcion="Cifrado de servidores",
        nivel=Nivel.ALTO,
        roles=["ti", "legal"],
        injects=[Inject(f"Inject {n}", "Detalle", orden=n) for n in (3, 1, 2)],
        tareas=[
            Tarea("¿Qué aísla primero?", "ti", Nivel.MEDIO, ["Segmenta la red"]),
            Tarea("¿Restaura respaldos?", "ti", Nivel.ALTO, ["Verifica integridad"]),
            Tarea("¿A quién notifica?", "legal", Nivel.BAJO, ["Regulador"]),
        ],
        estado=estado,
    )


def _sesion_lista() -> SesionTabletop:
    sesion = SesionTabletop.desde_escenario(_escenario(), MODERADOR)
    sesion.participantes = [
        ParticipanteSesion(uuid4(), "ti"),
        ParticipanteSesion(uuid4(), "legal"),
    ]
    sesion.fecha_programada = AHORA + timedelta(days=2)
    sesion.duracion_minutos = 90
    return sesion


def _errores_al_programar(sesion: SesionTabletop) -> list[str]:
    with pytest.raises(ReglaSesionError) as e:
        sesion.programar(AHORA)
    return e.value.errores


# --- Creación desde el escenario ------------------------------------------------


def test_desde_escenario_copia_contenido_con_ids_nuevos():
    escenario = _escenario()
    sesion = SesionTabletop.desde_escenario(escenario, MODERADOR)

    assert sesion.estado == EstadoSesion.BORRADOR
    assert sesion.nombre == escenario.nombre
    assert sesion.escenario_id == escenario.id
    assert sesion.roles == ["ti", "legal"]
    assert [i.orden for i in sesion.injects] == [1, 2, 3]
    assert {i.id for i in sesion.injects}.isdisjoint(i.id for i in escenario.injects)
    assert {t.id for t in sesion.tareas}.isdisjoint(t.id for t in escenario.tareas)
    assert all(t.tipo == TipoTarea.TEXTO_LIBRE for t in sesion.tareas)
    assert sesion.pesos == PesosPuntuacion(40, 40, 20)


def test_desde_escenario_reparte_las_tareas_de_cada_rol_entre_los_injects():
    sesion = SesionTabletop.desde_escenario(_escenario(), MODERADOR)
    primero, segundo, _ = sesion.injects

    ti = [t.inject_id for t in sesion.tareas if t.rol_codigo == "ti"]
    legal = [t.inject_id for t in sesion.tareas if t.rol_codigo == "legal"]
    assert ti == [primero.id, segundo.id]
    assert legal == [primero.id]


def test_editar_la_sesion_no_modifica_el_escenario():
    escenario = _escenario()
    sesion = SesionTabletop.desde_escenario(escenario, MODERADOR)

    sesion.tareas[0].criterios.append("Avisa al CISO")
    sesion.tareas[0].puntaje_maximo = 20

    assert escenario.tareas[0].criterios == ["Segmenta la red"]
    assert escenario.tareas[0].puntaje_maximo == 10


@pytest.mark.parametrize(
    "estado", [EstadoEscenario.BORRADOR, EstadoEscenario.ARCHIVADO]
)
def test_solo_se_usa_un_escenario_publicado(estado):
    with pytest.raises(ReglaSesionError):
        SesionTabletop.desde_escenario(_escenario(estado), MODERADOR)


def test_puntaje_maximo_total_se_calcula_solo():
    sesion = _sesion_lista()
    sesion.tareas[0].puntaje_maximo = 25
    assert sesion.puntaje_maximo_total == 25 + 10 + 10


# --- Programar --------------------------------------------------------------------


def test_programar_una_sesion_completa():
    sesion = _sesion_lista()
    sesion.programar(AHORA)
    assert sesion.estado == EstadoSesion.PROGRAMADA


def test_no_se_programa_sin_participante_para_cada_rol():
    sesion = _sesion_lista()
    sesion.participantes = [ParticipanteSesion(uuid4(), "ti")]
    assert "Falta al menos un participante para los roles: legal" in (
        _errores_al_programar(sesion)
    )


def test_no_se_programa_sin_roles():
    sesion = _sesion_lista()
    sesion.roles, sesion.tareas, sesion.participantes = [], [], []
    assert "Debe tener al menos un rol" in _errores_al_programar(sesion)


def test_no_se_programa_sin_tareas_para_un_rol():
    sesion = _sesion_lista()
    sesion.tareas = [t for t in sesion.tareas if t.rol_codigo == "ti"]
    assert "Faltan tareas para los roles: legal" in _errores_al_programar(sesion)


def test_no_se_programa_con_tareas_sin_inject():
    sesion = _sesion_lista()
    sesion.tareas[0].inject_id = None
    assert "Todas las tareas deben estar asignadas a un inject" in (
        _errores_al_programar(sesion)
    )


def test_texto_libre_necesita_criterios_para_programar():
    sesion = _sesion_lista()
    sesion.tareas[0].criterios = []
    assert any("criterio de evaluación" in e for e in _errores_al_programar(sesion))


def test_seleccion_multiple_necesita_opciones_y_una_correcta():
    sesion = _sesion_lista()
    tarea = sesion.tareas[0]
    tarea.tipo = TipoTarea.SELECCION_MULTIPLE
    tarea.opciones = [OpcionRespuesta("Sí")]

    errores = _errores_al_programar(sesion)
    assert any("al menos 2 opciones" in e for e in errores)
    assert any("no tiene una opción correcta" in e for e in errores)

    tarea.opciones = [OpcionRespuesta("Sí", correcta=True), OpcionRespuesta("No")]
    tarea.criterios = []  # la selección múltiple se evalúa con las opciones
    sesion.programar(AHORA)
    assert sesion.estado == EstadoSesion.PROGRAMADA


@pytest.mark.parametrize(
    ("fecha", "mensaje"),
    [
        (None, "Debe tener fecha y hora programadas"),
        (AHORA, "La fecha programada debe ser futura"),
        (AHORA - timedelta(hours=1), "La fecha programada debe ser futura"),
    ],
)
def test_no_se_programa_sin_fecha_futura(fecha, mensaje):
    sesion = _sesion_lista()
    sesion.fecha_programada = fecha
    assert mensaje in _errores_al_programar(sesion)


def test_no_se_programa_sin_duracion():
    sesion = _sesion_lista()
    sesion.duracion_minutos = None
    assert "Debe tener una duración" in _errores_al_programar(sesion)


def test_solo_se_programa_desde_borrador():
    sesion = _sesion_lista()
    sesion.programar(AHORA)
    with pytest.raises(ReglaSesionError):
        sesion.programar(AHORA)


# --- Consistencia (siempre, incluso en borrador) ----------------------------------


def test_un_borrador_incompleto_se_puede_guardar():
    sesion = SesionTabletop.desde_escenario(_escenario(), MODERADOR)
    nuevo = SesionTabletop.desde_escenario(_escenario(), MODERADOR, "Simulacro Q4")

    sesion.reemplazar_diseno(nuevo, AHORA)

    assert sesion.nombre == "Simulacro Q4"
    assert sesion.estado == EstadoSesion.BORRADOR


@pytest.mark.parametrize(
    ("pesos", "mensaje"),
    [
        (PesosPuntuacion(50, 40, 20), "Los pesos de puntuación deben sumar 100"),
        (PesosPuntuacion(110, 10, -20), "no pueden ser negativos"),
    ],
)
def test_los_pesos_deben_sumar_100(pesos, mensaje):
    sesion = _sesion_lista()
    sesion.pesos = pesos
    with pytest.raises(ReglaSesionError) as e:
        sesion.validar_consistencia()
    assert any(mensaje in err for err in e.value.errores)


def test_participante_con_un_solo_rol():
    sesion = _sesion_lista()
    usuario = uuid4()
    sesion.participantes = [
        ParticipanteSesion(usuario, "ti"),
        ParticipanteSesion(usuario, "legal"),
    ]
    with pytest.raises(ReglaSesionError) as e:
        sesion.validar_consistencia()
    assert "Un participante solo puede tener un rol en la sesión" in e.value.errores


def test_participantes_y_tareas_deben_usar_roles_de_la_sesion():
    sesion = _sesion_lista()
    sesion.roles = ["ti"]

    with pytest.raises(ReglaSesionError) as e:
        sesion.validar_consistencia()
    assert "Hay tareas para roles que no están en la sesión: legal" in e.value.errores
    assert (
        "Hay participantes con roles que no están en la sesión: legal"
        in e.value.errores
    )


def test_tarea_en_un_inject_ajeno():
    sesion = _sesion_lista()
    sesion.tareas[0].inject_id = uuid4()
    with pytest.raises(ReglaSesionError) as e:
        sesion.validar_consistencia()
    assert "Hay tareas asignadas a un inject que no está en la sesión" in (
        e.value.errores
    )


def test_texto_libre_no_lleva_opciones():
    sesion = _sesion_lista()
    sesion.tareas[0].opciones = [OpcionRespuesta("Sí", correcta=True)]
    with pytest.raises(ReglaSesionError) as e:
        sesion.validar_consistencia()
    assert "Las tareas de texto libre no llevan opciones" in e.value.errores


# --- Edición ----------------------------------------------------------------------


def test_una_sesion_programada_debe_seguir_completa_al_editarla():
    sesion = _sesion_lista()
    sesion.programar(AHORA)
    incompleta = _sesion_lista()
    incompleta.participantes = []

    with pytest.raises(ReglaSesionError):
        sesion.reemplazar_diseno(incompleta, AHORA)
    assert len(sesion.participantes) == 2


def test_una_sesion_en_curso_no_se_edita():
    sesion = _sesion_lista()
    sesion.estado = EstadoSesion.EN_CURSO
    with pytest.raises(ReglaSesionError):
        sesion.reemplazar_diseno(_sesion_lista(), AHORA)
