"""Límite configurable de sesiones activas simultáneas (PC-24, RNF).

Con dobles en memoria (sin PostgreSQL). La prueba de concurrencia real con
el advisory lock de PostgreSQL vive en test_limite_sesiones_pg.py.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo, excede_duracion
from app.domain.escenarios import Escenario, EstadoEscenario, Inject, Nivel, Tarea
from app.domain.sesiones import EstadoSesion, ReglaSesionError, SesionTabletop
from tests.fakes import RepoSesionesEnMemoria

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


class _Reloj:
    """Reloj controlable a mano, para simular que el tiempo avanza."""

    def __init__(self, ahora: datetime):
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora


def _escenario() -> Escenario:
    return Escenario(
        "Ransomware en sucursal",
        "ransomware",
        "Cifrado de servidores",
        Nivel.ALTO,
        ["ti"],
        injects=[Inject("Detección inicial", "TI detecta archivos cifrados", orden=1)],
        tareas=[Tarea("¿Qué aísla primero?", "ti", Nivel.MEDIO, ["Segmenta"])],
        estado=EstadoEscenario.PUBLICADO,
    )


def _sesion_programada(duracion_minutos: int = 60) -> SesionTabletop:
    sesion = SesionTabletop.desde_escenario(_escenario(), uuid4(), "Simulacro")
    sesion.fecha_programada = T0 - timedelta(days=1)
    sesion.duracion_minutos = duracion_minutos
    sesion.estado = EstadoSesion.PROGRAMADA
    return sesion


def _nueva_sesion_programada(
    repo: RepoSesionesEnMemoria, duracion_minutos: int = 60
) -> tuple:
    sesion = repo.guardar(_sesion_programada(duracion_minutos))
    return sesion.id, sesion.moderador_id


def test_la_sesion_11_se_rechaza_con_el_limite_por_defecto():
    repo = RepoSesionesEnMemoria()
    servicio = ServicioEnVivo(repo, EnVivoEnMemoria(), reloj=lambda: T0)
    for _ in range(10):
        sesion_id, moderador_id = _nueva_sesion_programada(repo)
        servicio.iniciar(sesion_id, moderador_id)

    sesion_id, moderador_id = _nueva_sesion_programada(repo)
    with pytest.raises(ReglaSesionError, match="máximo de 10 sesiones activas"):
        servicio.iniciar(sesion_id, moderador_id)


def test_el_limite_configurado_se_respeta():
    repo = RepoSesionesEnMemoria()
    servicio = ServicioEnVivo(
        repo, EnVivoEnMemoria(), reloj=lambda: T0, maximo_activas=2
    )
    for _ in range(2):
        sesion_id, moderador_id = _nueva_sesion_programada(repo)
        servicio.iniciar(sesion_id, moderador_id)

    sesion_id, moderador_id = _nueva_sesion_programada(repo)
    with pytest.raises(ReglaSesionError, match="máximo de 2 sesiones activas"):
        servicio.iniciar(sesion_id, moderador_id)


def test_cerrar_una_sesion_libera_un_cupo():
    repo = RepoSesionesEnMemoria()
    servicio = ServicioEnVivo(
        repo, EnVivoEnMemoria(), reloj=lambda: T0, maximo_activas=1
    )
    primera_id, primer_moderador = _nueva_sesion_programada(repo)
    servicio.iniciar(primera_id, primer_moderador)

    segunda_id, segundo_moderador = _nueva_sesion_programada(repo)
    with pytest.raises(ReglaSesionError, match="máximo de 1 sesiones activas"):
        servicio.iniciar(segunda_id, segundo_moderador)

    servicio.cerrar(primera_id, primer_moderador)
    servicio.iniciar(segunda_id, segundo_moderador)  # ya hay cupo de nuevo


def test_el_mensaje_de_limite_menciona_sesiones_que_exceden_su_duracion():
    repo = RepoSesionesEnMemoria()
    reloj = _Reloj(T0)
    servicio = ServicioEnVivo(repo, EnVivoEnMemoria(), reloj=reloj, maximo_activas=1)
    sesion_id, moderador_id = _nueva_sesion_programada(repo, duracion_minutos=10)
    servicio.iniciar(sesion_id, moderador_id)

    reloj.ahora = T0 + timedelta(hours=2)  # excede los 10 minutos programados
    otra_id, otro_moderador = _nueva_sesion_programada(repo)
    with pytest.raises(
        ReglaSesionError,
        match="1 de las sesiones activas ya supera su duración programada",
    ):
        servicio.iniciar(otra_id, otro_moderador)


def test_excede_duracion_es_falso_sin_iniciar_o_sin_duracion_programada():
    sesion = _sesion_programada(duracion_minutos=10)
    assert excede_duracion(sesion, T0) is False  # todavía no se inició

    sesion.iniciada_en = T0
    sesion.duracion_minutos = None
    assert excede_duracion(sesion, T0 + timedelta(hours=5)) is False


def test_excede_duracion_compara_contra_la_duracion_programada():
    sesion = _sesion_programada(duracion_minutos=30)
    sesion.iniciar(T0)

    assert excede_duracion(sesion, T0 + timedelta(minutes=20)) is False
    assert excede_duracion(sesion, T0 + timedelta(minutes=31)) is True
