"""Modelo ORM de las respuestas de los participantes (PB-08, migración 0007)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence.database import Base


class RespuestaModel(Base):
    __tablename__ = "respuesta"
    # Una sola respuesta por participante y tarea: la base es la última barrera.
    __table_args__ = (
        UniqueConstraint("tarea_id", "usuario_id", name="uq_respuesta_tarea_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="RESTRICT"), index=True
    )
    tarea_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion_tarea.id", ondelete="RESTRICT")
    )
    inject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion_inject.id", ondelete="RESTRICT")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT")
    )
    rol_codigo: Mapped[str] = mapped_column(
        String(40), ForeignKey("rol_ejercicio.codigo")
    )
    texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    opciones_elegidas: Mapped[list[int]] = mapped_column(JSON)
    recibida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    segundos_usados: Mapped[int] = mapped_column(Integer)
