"""Conversión del estado y los eventos en vivo a JSON y de vuelta (para Redis)."""

from datetime import datetime
from uuid import UUID

from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo

_FECHAS = ("iniciada_en", "inject_lanzado_en", "pausada_desde", "finalizada_en")


def estado_a_dict(e: EstadoEnVivo) -> dict:
    datos = {
        "sesion_id": str(e.sesion_id),
        "total_injects": e.total_injects,
        "inject_actual": e.inject_actual,
        "segundos_en_pausa": e.segundos_en_pausa,
        "version": e.version,
        # JSON solo admite claves de texto.
        "lanzamientos": {str(k): v for k, v in e.lanzamientos.items()},
    }
    for campo in _FECHAS:
        valor = getattr(e, campo)
        datos[campo] = valor.isoformat() if valor else None
    return datos


def estado_desde_dict(d: dict) -> EstadoEnVivo:
    fechas = {c: datetime.fromisoformat(d[c]) if d.get(c) else None for c in _FECHAS}
    return EstadoEnVivo(
        sesion_id=UUID(d["sesion_id"]),
        total_injects=d["total_injects"],
        inject_actual=d["inject_actual"],
        segundos_en_pausa=d["segundos_en_pausa"],
        version=d["version"],
        lanzamientos={int(k): v for k, v in d.get("lanzamientos", {}).items()},
        **fechas,
    )


def evento_a_dict(e: EventoEnVivo) -> dict:
    return {
        "sesion_id": str(e.sesion_id),
        "tipo": e.tipo,
        "estado": estado_a_dict(e.estado) if e.estado else None,
        "conectados": sorted(str(u) for u in e.conectados),
    }


def evento_desde_dict(d: dict) -> EventoEnVivo:
    return EventoEnVivo(
        sesion_id=UUID(d["sesion_id"]),
        tipo=d["tipo"],
        estado=estado_desde_dict(d["estado"]) if d.get("estado") else None,
        conectados=frozenset(UUID(u) for u in d.get("conectados", [])),
    )
