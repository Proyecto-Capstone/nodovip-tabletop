"""Implementación SQLAlchemy del puerto de reportes (adaptador de salida)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, defer

from app.adapters.outbound.persistence.models_reportes import ReporteModel
from app.domain.reportes import EstadoReporte, ReporteGuardado


def _a_dominio(m: ReporteModel, con_pdf: bool = True) -> ReporteGuardado:
    return ReporteGuardado(
        sesion_id=m.sesion_id,
        estado=EstadoReporte(m.estado),
        solicitado_en=m.solicitado_en,
        generado_en=m.generado_en,
        pdf=m.pdf if con_pdf else None,
        error=m.error,
    )


class SqlReporteRepository:
    def __init__(self, session: Session):
        self.session = session

    def obtener(self, sesion_id: UUID) -> ReporteGuardado | None:
        m = self.session.get(ReporteModel, sesion_id)
        return _a_dominio(m) if m else None

    def estados(self, sesion_ids: list[UUID]) -> dict[UUID, ReporteGuardado]:
        if not sesion_ids:
            return {}
        filas = self.session.scalars(
            select(ReporteModel)
            .options(defer(ReporteModel.pdf))
            .where(ReporteModel.sesion_id.in_(sesion_ids))
        )
        return {m.sesion_id: _a_dominio(m, con_pdf=False) for m in filas}

    def marcar_generando(self, sesion_id: UUID, cuando: datetime) -> None:
        m = self._fila(sesion_id)
        m.estado = EstadoReporte.GENERANDO.value
        m.solicitado_en = cuando
        m.error = None
        self.session.commit()

    def guardar_pdf(self, sesion_id: UUID, pdf: bytes, cuando: datetime) -> None:
        m = self._fila(sesion_id)
        m.estado = EstadoReporte.GENERADO.value
        m.pdf = pdf
        m.generado_en = cuando
        m.error = None
        self.session.commit()

    def marcar_fallido(self, sesion_id: UUID, error: str, cuando: datetime) -> None:
        m = self._fila(sesion_id)
        m.estado = EstadoReporte.FALLIDO.value
        m.error = error
        m.solicitado_en = m.solicitado_en or cuando
        self.session.commit()

    def _fila(self, sesion_id: UUID) -> ReporteModel:
        m = self.session.get(ReporteModel, sesion_id)
        if m is None:
            m = ReporteModel(sesion_id=sesion_id)
            self.session.add(m)
        return m
