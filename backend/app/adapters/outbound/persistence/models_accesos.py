"""Modelo ORM del historial de accesos (PB-01, RNF-01). Adaptador de salida."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence.database import Base


class AccesoModel(Base):
    __tablename__ = "acceso"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # NULL cuando el correo ingresado no corresponde a ningún usuario.
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=True
    )
    correo_ingresado: Mapped[str] = mapped_column(String(255))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ip: Mapped[str] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resultado: Mapped[str] = mapped_column(String(30))
