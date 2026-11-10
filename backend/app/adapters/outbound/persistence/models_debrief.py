"""Modelo ORM del debrief de cada sesión (PC-45, migración 0012)."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence.database import Base


class DebriefModel(Base):
    __tablename__ = "debrief"

    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="RESTRICT"), primary_key=True
    )
    autor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT"), index=True
    )
    fortalezas: Mapped[list] = mapped_column(JSON)
    mejoras: Mapped[list] = mapped_column(JSON)
    acciones: Mapped[list] = mapped_column(JSON)
    estado: Mapped[str] = mapped_column(String(12))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
