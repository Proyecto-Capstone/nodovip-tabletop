"""Modelos ORM de las sesiones tabletop (adaptador de salida, PB-05)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.outbound.persistence.database import Base
from app.adapters.outbound.persistence.models_escenarios import RolEjercicioModel

sesion_rol = Table(
    "sesion_rol",
    Base.metadata,
    Column(
        "sesion_id",
        Uuid,
        ForeignKey("sesion.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "rol_codigo",
        String(40),
        ForeignKey("rol_ejercicio.codigo"),
        primary_key=True,
    ),
)


class SesionModel(Base):
    __tablename__ = "sesion"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    escenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("escenario.id", ondelete="RESTRICT"), index=True
    )
    moderador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT"), index=True
    )
    estado: Mapped[str] = mapped_column(String(15), index=True)
    fecha_programada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duracion_minutos: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Ejecución en vivo (PB-07, migración 0006).
    iniciada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalizada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    inject_actual: Mapped[int] = mapped_column(SmallInteger, default=0)
    peso_completitud: Mapped[int] = mapped_column(SmallInteger)
    peso_precision: Mapped[int] = mapped_column(SmallInteger)
    peso_tiempo: Mapped[int] = mapped_column(SmallInteger)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[RolEjercicioModel]] = relationship(secondary=sesion_rol)
    injects: Mapped[list["SesionInjectModel"]] = relationship(
        cascade="all, delete-orphan", order_by="SesionInjectModel.orden"
    )
    tareas: Mapped[list["SesionTareaModel"]] = relationship(
        cascade="all, delete-orphan", order_by="SesionTareaModel.posicion"
    )
    participantes: Mapped[list["SesionParticipanteModel"]] = relationship(
        cascade="all, delete-orphan"
    )


class SesionInjectModel(Base):
    __tablename__ = "sesion_inject"
    __table_args__ = (UniqueConstraint("sesion_id", "orden"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="CASCADE"), index=True
    )
    orden: Mapped[int] = mapped_column(SmallInteger)
    titulo: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str] = mapped_column(Text)
    minuto_sugerido: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class SesionTareaModel(Base):
    __tablename__ = "sesion_tarea"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="CASCADE"), index=True
    )
    inject_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sesion_inject.id", ondelete="SET NULL"), nullable=True
    )
    posicion: Mapped[int] = mapped_column(SmallInteger)
    rol_codigo: Mapped[str] = mapped_column(
        String(40), ForeignKey("rol_ejercicio.codigo")
    )
    tipo: Mapped[str] = mapped_column(String(20))
    enunciado: Mapped[str] = mapped_column(Text)
    opciones: Mapped[list[dict]] = mapped_column(JSON)
    criterios: Mapped[list[str]] = mapped_column(JSON)
    dificultad: Mapped[str] = mapped_column(String(10))
    puntaje_maximo: Mapped[int] = mapped_column(SmallInteger)
    tiempo_limite_segundos: Mapped[int] = mapped_column(Integer)
    respuesta_esperada: Mapped[str | None] = mapped_column(Text, nullable=True)


class SesionParticipanteModel(Base):
    __tablename__ = "sesion_participante"

    sesion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sesion.id", ondelete="CASCADE"), primary_key=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="RESTRICT"), primary_key=True
    )
    rol_codigo: Mapped[str] = mapped_column(
        String(40), ForeignKey("rol_ejercicio.codigo")
    )
    # PB-06: seguimiento de la invitación por correo.
    invitacion: Mapped[str] = mapped_column(String(15), default="pendiente")
    invitacion_enviada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invitacion_aceptada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invitacion_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
