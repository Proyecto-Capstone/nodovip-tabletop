"""Puertos de salida del reporte de brechas (PB-14)."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.reportes import ReporteGuardado, ReporteSesion


class GeneradorPdf(Protocol):
    """Convierte el contenido del reporte en un PDF (adaptador: WeasyPrint)."""

    def generar(self, reporte: ReporteSesion) -> bytes: ...


class ReporteRepository(Protocol):
    def obtener(self, sesion_id: UUID) -> ReporteGuardado | None: ...

    def estados(self, sesion_ids: list[UUID]) -> dict[UUID, ReporteGuardado]:
        """Estado de varios reportes, sin cargar los PDF."""
        ...

    def marcar_generando(self, sesion_id: UUID, cuando: datetime) -> None: ...

    def guardar_pdf(self, sesion_id: UUID, pdf: bytes, cuando: datetime) -> None: ...

    def marcar_fallido(self, sesion_id: UUID, error: str, cuando: datetime) -> None: ...
