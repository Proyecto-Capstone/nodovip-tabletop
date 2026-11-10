"""Reglas del debrief (PC-45)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.domain.debrief import (
    AccionMejora,
    Debrief,
    EstadoDebrief,
    PrioridadAccion,
    ReglaDebriefError,
)

AHORA = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
ROLES = {"ti", "legal"}


def _debrief() -> Debrief:
    return Debrief(uuid4(), uuid4(), AHORA, AHORA)


def _accion(**cambios) -> AccionMejora:
    datos = {
        "descripcion": "Probar la restauración de respaldos cada mes",
        "prioridad": PrioridadAccion.ALTA,
        "rol_codigo": "ti",
        "plazo": date(2026, 12, 15),
    }
    datos.update(cambios)
    return AccionMejora(**datos)


def test_editar_limpia_espacios_y_elementos_vacios():
    d = _debrief()
    d.editar(
        ["  Escalaron rápido  ", "", "   "],
        ["Faltó coordinar con Legal"],
        [_accion(descripcion="  Simulacro trimestral  "), _accion(descripcion=" ")],
        ROLES,
        AHORA,
    )
    assert d.fortalezas == ["Escalaron rápido"]
    assert d.acciones[0].descripcion == "Simulacro trimestral"
    assert len(d.acciones) == 1


def test_editar_valida_formato_y_rol_responsable():
    d = _debrief()
    with pytest.raises(ReglaDebriefError) as e:
        d.editar(
            ["x" * 1001],
            [],
            [_accion(descripcion="abc"), _accion(rol_codigo="rrhh")],
            ROLES,
            AHORA,
        )
    assert e.value.errores == [
        "Fortalezas: cada elemento admite hasta 1000 caracteres",
        "Acción 1: la descripción debe tener entre 5 y 500 caracteres",
        "Acción 2: el rol responsable no es de esta sesión",
    ]


def test_sin_rol_responsable_es_de_toda_la_organizacion():
    d = _debrief()
    d.editar([], [], [_accion(rol_codigo=None)], ROLES, AHORA)
    assert d.acciones[0].rol_codigo is None


def test_completar_exige_contenido_y_plazos_validos():
    d = _debrief()
    with pytest.raises(ReglaDebriefError) as e:
        d.completar(AHORA)
    assert e.value.errores == [
        "Registra al menos una fortaleza",
        "Registra al menos un aspecto a mejorar",
        "Agrega al menos una acción al plan",
    ]
    d.editar(
        ["Buena comunicación"],
        ["Respaldos sin probar"],
        [_accion(plazo=None), _accion(plazo=date(2026, 11, 1))],
        ROLES,
        AHORA,
    )
    with pytest.raises(ReglaDebriefError) as e:
        d.completar(AHORA)
    assert e.value.errores == [
        "Acción 1: indica un plazo",
        "Acción 2: el plazo no puede estar en el pasado",
    ]


def test_completado_no_se_edita_hasta_reabrirlo():
    d = _debrief()
    d.editar(
        ["Buena comunicación"], ["Respaldos sin probar"], [_accion()], ROLES, AHORA
    )
    d.completar(AHORA)
    assert d.estado == EstadoDebrief.COMPLETADO and d.completado_en == AHORA
    with pytest.raises(ReglaDebriefError):
        d.editar([], [], [], ROLES, AHORA)
    with pytest.raises(ReglaDebriefError):
        d.completar(AHORA)

    d.reabrir(AHORA)
    assert d.estado == EstadoDebrief.BORRADOR and d.completado_en is None
    d.editar(["Otra"], ["Otra mejora"], [_accion()], ROLES, AHORA)
    with pytest.raises(ReglaDebriefError):
        d.reabrir(AHORA)


def test_accion_ida_y_vuelta_a_json():
    a = _accion()
    assert AccionMejora.desde_dict(a.a_dict()) == a
    sin_plazo = _accion(plazo=None, rol_codigo=None)
    assert AccionMejora.desde_dict(sin_plazo.a_dict()) == sin_plazo
