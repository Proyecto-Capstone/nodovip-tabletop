"""Estado en vivo de la sesión (PB-07). Sin Redis ni base de datos."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.outbound.en_vivo.serializacion import (
    estado_a_dict,
    estado_desde_dict,
    evento_a_dict,
    evento_desde_dict,
)
from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo
from app.domain.escenarios import Escenario, EstadoEscenario, Inject, Nivel, Tarea
from app.domain.sesiones import EstadoSesion, ReglaSesionError, SesionTabletop

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def _estado(total=3) -> EstadoEnVivo:
    return EstadoEnVivo(uuid4(), total_injects=total, iniciada_en=T0)


def test_lanzar_injects_en_orden_hasta_el_ultimo():
    e = _estado(total=2)
    e.lanzar_siguiente_inject(T0 + timedelta(minutes=1))
    e.lanzar_siguiente_inject(T0 + timedelta(minutes=5))

    assert e.inject_actual == 2
    assert e.inject_lanzado_en == T0 + timedelta(minutes=5)
    assert e.version == 3
    with pytest.raises(ReglaSesionError, match="todos los injects"):
        e.lanzar_siguiente_inject(T0 + timedelta(minutes=6))


def test_el_tiempo_no_corre_en_pausa():
    e = _estado()
    e.pausar(T0 + timedelta(minutes=10))
    assert e.segundos_transcurridos(T0 + timedelta(minutes=15)) == 600

    e.reanudar(T0 + timedelta(minutes=20))
    assert e.segundos_transcurridos(T0 + timedelta(minutes=25)) == 900


def test_en_pausa_no_se_lanzan_injects():
    e = _estado()
    e.pausar(T0)
    with pytest.raises(ReglaSesionError, match="Reanuda"):
        e.lanzar_siguiente_inject(T0)
    with pytest.raises(ReglaSesionError, match="ya está en pausa"):
        e.pausar(T0)


def test_cerrar_en_pausa_descuenta_la_pausa_y_congela_el_tiempo():
    e = _estado()
    e.pausar(T0 + timedelta(minutes=30))
    e.cerrar(T0 + timedelta(minutes=40))

    assert e.cerrada and not e.pausada
    assert e.segundos_transcurridos(T0 + timedelta(hours=5)) == 1800
    with pytest.raises(ReglaSesionError, match="ya terminó"):
        e.lanzar_siguiente_inject(T0 + timedelta(hours=5))


def test_serializacion_para_redis_ida_y_vuelta():
    e = _estado()
    e.lanzar_siguiente_inject(T0 + timedelta(minutes=2))
    e.pausar(T0 + timedelta(minutes=3))

    assert estado_desde_dict(estado_a_dict(e)) == e
    evento = EventoEnVivo(
        e.sesion_id, "estado", estado=e, conectados=frozenset({uuid4()})
    )
    assert evento_desde_dict(evento_a_dict(evento)) == evento


def _sesion(estado: EstadoSesion) -> SesionTabletop:
    escenario = Escenario(
        "Ransomware",
        "ransomware",
        "Cifrado de servidores",
        Nivel.ALTO,
        ["ti"],
        injects=[Inject("Inject 1", "Detalle", orden=1)],
        tareas=[Tarea("¿Qué aísla primero?", "ti", Nivel.MEDIO, ["Segmenta"])],
        estado=EstadoEscenario.PUBLICADO,
    )
    sesion = SesionTabletop.desde_escenario(escenario, uuid4())
    sesion.estado = estado
    return sesion


def test_solo_se_inicia_una_sesion_programada_y_solo_se_cierra_en_curso():
    with pytest.raises(ReglaSesionError):
        _sesion(EstadoSesion.BORRADOR).iniciar(T0)
    with pytest.raises(ReglaSesionError):
        _sesion(EstadoSesion.PROGRAMADA).finalizar(T0, 0)

    sesion = _sesion(EstadoSesion.PROGRAMADA)
    sesion.iniciar(T0)
    assert sesion.estado == EstadoSesion.EN_CURSO and sesion.iniciada_en == T0
    sesion.finalizar(T0 + timedelta(hours=1), inject_actual=1)
    assert sesion.estado == EstadoSesion.FINALIZADA
    assert sesion.inject_actual == 1
