"""Reglas de negocio de escenarios (RF-04). No necesitan base de datos."""

import pytest

from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    ReglaEscenarioError,
    Tarea,
)


def _tarea(rol: str) -> Tarea:
    return Tarea(
        enunciado="¿Qué hace primero?",
        rol_codigo=rol,
        dificultad=Nivel.MEDIO,
        criterios=["Aísla la red"],
    )


def _escenario(injects: int = 3, roles=("ti", "legal"), tareas=("ti", "legal")):
    return Escenario(
        nombre="Prueba",
        tipo_codigo="ransomware",
        descripcion="Descripción de prueba",
        nivel=Nivel.ALTO,
        roles=list(roles),
        injects=[
            Inject(titulo=f"Inject {n}", descripcion="Algo pasa", orden=n)
            for n in range(1, injects + 1)
        ],
        tareas=[_tarea(r) for r in tareas],
    )


def test_escenario_completo_se_publica():
    escenario = _escenario()
    escenario.publicar()
    assert escenario.estado == EstadoEscenario.PUBLICADO


def test_no_se_publica_con_menos_de_tres_injects():
    escenario = _escenario(injects=2)
    with pytest.raises(ReglaEscenarioError, match="al menos 3 injects"):
        escenario.publicar()
    assert escenario.estado == EstadoEscenario.BORRADOR


def test_no_se_publica_si_un_rol_no_tiene_tareas():
    escenario = _escenario(tareas=("ti",))
    with pytest.raises(ReglaEscenarioError, match="legal"):
        escenario.publicar()


def test_tarea_para_rol_ajeno_es_inconsistente():
    escenario = _escenario(tareas=("ti", "legal", "rrhh"))
    with pytest.raises(ReglaEscenarioError, match="rrhh"):
        escenario.validar_consistencia()


def test_borrador_incompleto_es_valido():
    escenario = _escenario(injects=0, tareas=())
    escenario.validar_consistencia()
    assert len(escenario.errores_para_publicar()) == 2


def test_editar_publicado_exige_que_siga_siendo_publicable():
    escenario = _escenario()
    escenario.publicar()
    with pytest.raises(ReglaEscenarioError):
        escenario.reemplazar_contenido(_escenario(injects=1))
    assert len(escenario.injects) == 3


def test_archivado_no_se_publica_ni_se_edita():
    escenario = _escenario()
    escenario.archivar()
    with pytest.raises(ReglaEscenarioError):
        escenario.publicar()
    with pytest.raises(ReglaEscenarioError):
        escenario.reemplazar_contenido(_escenario())
