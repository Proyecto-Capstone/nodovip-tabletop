"""Implementación SQLAlchemy del puerto del debrief (adaptador de salida)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_debrief import DebriefModel
from app.domain.debrief import AccionMejora, Debrief, EstadoDebrief


def _a_dominio(m: DebriefModel) -> Debrief:
    return Debrief(
        sesion_id=m.sesion_id,
        autor_id=m.autor_id,
        creado_en=m.creado_en,
        actualizado_en=m.actualizado_en,
        fortalezas=list(m.fortalezas),
        mejoras=list(m.mejoras),
        acciones=[AccionMejora.desde_dict(a) for a in m.acciones],
        estado=EstadoDebrief(m.estado),
        completado_en=m.completado_en,
    )


class SqlDebriefRepository:
    def __init__(self, session: Session):
        self.session = session

    def obtener(self, sesion_id: UUID) -> Debrief | None:
        m = self.session.get(DebriefModel, sesion_id)
        return _a_dominio(m) if m else None

    def guardar(self, debrief: Debrief) -> Debrief:
        m = self.session.get(DebriefModel, debrief.sesion_id)
        if m is None:
            m = DebriefModel(sesion_id=debrief.sesion_id, creado_en=debrief.creado_en)
            self.session.add(m)
        m.autor_id = debrief.autor_id
        m.fortalezas = list(debrief.fortalezas)
        m.mejoras = list(debrief.mejoras)
        m.acciones = [a.a_dict() for a in debrief.acciones]
        m.estado = debrief.estado.value
        m.actualizado_en = debrief.actualizado_en
        m.completado_en = debrief.completado_en
        self.session.commit()
        return _a_dominio(m)
