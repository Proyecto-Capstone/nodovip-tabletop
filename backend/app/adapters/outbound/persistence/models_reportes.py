"""Modelo ORM del reporte PDF de cada sesión (PB-14, migración 0010)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence.database import Base


class ReporteModel(Base):
    __tablename__ = "reporte"

    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="RESTRICT"), primary_key=True
    )
    estado: Mapped[str] = mapped_column(String(12))
    solicitado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pdf: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
