"""Catálogo de escenarios profesionales y su carga (PC-46)."""

import re
from uuid import uuid4

import pytest

from app.application.escenarios import ServicioEscenarios
from app.catalogo_escenarios import CATALOGO
from app.domain.escenarios import (
    EstadoEscenario,
    Nivel,
    RolEjercicio,
    TipoEscenario,
    TipoTarea,
)
from app.domain.sesiones import SesionTabletop
from app.ports.escenario_repository import FiltroEscenarios
from app.seed_escenarios import cargar
from tests.test_api_escenarios import RepoEnMemoria

ROLES = [
    "ciso",
    "director_ejecutivo",
    "direccion",
    "legal",
    "ti",
    "comunicaciones",
    "relaciones_publicas",
    "operaciones",
    "atencion_cliente",
    "rrhh",
]
TIPOS = [
    "ransomware",
    "data_breach",
    "ddos",
    "phishing_dirigido",
    "insider_threat",
    "fallo_proveedor",
    "cadena_suministro",
]


class CatalogoCompleto:
    """Los 7 tipos y 10 roles que carga la migración 0002."""

    def tipos_escenario(self):
        return [TipoEscenario(c, c, c, Nivel.MEDIO, []) for c in TIPOS]

    def roles_ejercicio(self):
        return [RolEjercicio(c, c) for c in ROLES]


ESCENARIOS = [f() for f in CATALOGO]


def test_hay_seis_escenarios_de_tipos_distintos_y_nombres_unicos():
    assert len(ESCENARIOS) == 6
    assert len({e.tipo_codigo for e in ESCENARIOS}) == 6
    assert len({e.nombre for e in ESCENARIOS}) == 6
    assert all(e.tipo_codigo in TIPOS for e in ESCENARIOS)


@pytest.mark.parametrize("e", ESCENARIOS, ids=lambda e: e.tipo_codigo)
def test_cada_escenario_esta_listo_para_publicar(e):
    e.validar_consistencia()
    assert e.errores_para_publicar() == []
    assert set(e.roles) <= set(ROLES)


@pytest.mark.parametrize("e", ESCENARIOS, ids=lambda e: e.tipo_codigo)
def test_cuatro_injects_con_evidencia_y_preguntas_en_cada_uno(e):
    assert [i.orden for i in e.injects] == [1, 2, 3, 4]
    assert all(i.evidencia is not None for i in e.injects)
    # Variedad: al menos 3 tipos de evidencia distintos por escenario.
    assert len({i.evidencia.tipo for i in e.injects}) >= 3
    con_tarea = {t.inject_orden for t in e.tareas}
    assert con_tarea == {1, 2, 3, 4}


@pytest.mark.parametrize("e", ESCENARIOS, ids=lambda e: e.tipo_codigo)
def test_preguntas_de_cada_rol_y_de_ambos_tipos(e):
    assert {t.rol_codigo for t in e.tareas} == set(e.roles)
    seleccion = [t for t in e.tareas if t.tipo == TipoTarea.SELECCION_MULTIPLE]
    assert len(seleccion) >= 2
    for t in seleccion:
        assert sum(o.correcta for o in t.opciones) == 1, t.enunciado
        assert len(t.opciones) >= 3, t.enunciado
    for t in e.tareas:
        if t.tipo == TipoTarea.TEXTO_LIBRE:
            assert len(t.criterios) >= 3, t.enunciado


@pytest.mark.parametrize("e", ESCENARIOS, ids=lambda e: e.tipo_codigo)
def test_solo_correos_y_dominios_ficticios(e):
    """RNF-02: ningún correo ni dominio que pueda ser real."""
    textos = [e.descripcion] + [
        f"{i.evidencia.origen} {i.evidencia.contenido}"
        for i in e.injects
        if i.evidencia
    ]
    for texto in textos:
        for correo in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", texto):
            assert correo.endswith((".test", ".example")), correo
        for url in re.findall(r"https?://([^/\s]+)", texto):
            assert url.endswith((".test", ".example")), url


@pytest.mark.parametrize("e", ESCENARIOS, ids=lambda e: e.tipo_codigo)
def test_la_sesion_respeta_el_inject_de_cada_pregunta(e):
    e.estado = EstadoEscenario.PUBLICADO
    sesion = SesionTabletop.desde_escenario(e, uuid4())
    orden = {i.id: i.orden for i in sesion.injects}
    assert [orden[t.inject_id] for t in sesion.tareas] == [
        t.inject_orden for t in e.tareas
    ]
    # La selección múltiple llega con sus opciones y la sesión se puede programar.
    assert all(t.errores_para_programar() == [] for t in sesion.tareas)


def test_la_carga_es_idempotente_y_puede_actualizar():
    servicio = ServicioEscenarios(RepoEnMemoria(), CatalogoCompleto())
    primera = cargar(servicio)
    assert len(primera.creados) == 6
    # Quedan publicados: el moderador los ve en la biblioteca.
    assert len(servicio.listar(FiltroEscenarios(), puede_gestionar=False)) == 6

    segunda = cargar(servicio)
    assert segunda.creados == [] and len(segunda.sin_cambios) == 6

    # Si alguien editó un escenario, --actualizar lo vuelve al catálogo.
    [ransomware] = [
        e for e in servicio.repo.datos.values() if e.tipo_codigo == "ransomware"
    ]
    ransomware.descripcion = "Editado a mano para la prueba"
    servicio.repo.guardar(ransomware)
    tercera = cargar(servicio, actualizar=True)
    assert len(tercera.actualizados) == 6
    actualizado = servicio.repo.obtener(ransomware.id)
    assert actualizado.descripcion.startswith("Un lunes a las 07:40")
    assert actualizado.estado == EstadoEscenario.PUBLICADO
    assert len(servicio.repo.datos) == 6
