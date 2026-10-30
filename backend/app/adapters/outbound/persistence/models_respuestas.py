"""Modelos ORM de respuestas (PB-08, 0007) y su evaluación (PB-10, 0009)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
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
    # Evaluación automática al recibirla (PB-10). NULL en respuestas anteriores.
    puntaje_automatico: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    puntaje_maximo: Mapped[int | None] = mapped_column(SmallInteger)
    eval_completitud: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    eval_precision: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    eval_tiempo: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    eval_detalle: Mapped[dict | None] = mapped_column(JSON)


class AjustePuntajeModel(Base):
    """Cambio manual de puntaje del moderador. Solo inserción (trigger 0009)."""

    __tablename__ = "ajuste_puntaje"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    respuesta_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("respuesta.id", ondelete="RESTRICT")
    )
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="RESTRICT")
    )
    moderador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT")
    )
    puntaje_anterior: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    puntaje_nuevo: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    motivo: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
