"""Modelos ORM de la biblioteca de escenarios (adaptador de salida)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
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

escenario_rol = Table(
    "escenario_rol",
    Base.metadata,
    Column(
        "escenario_id",
        Uuid,
        ForeignKey("escenario.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "rol_codigo",
        String(40),
        ForeignKey("rol_ejercicio.codigo"),
        primary_key=True,
    ),
)


class TipoEscenarioModel(Base):
    __tablename__ = "tipo_escenario"

    codigo: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(Text)
    nivel_complejidad: Mapped[str] = mapped_column(String(10))
    roles_sugeridos: Mapped[list[str]] = mapped_column(JSON)


class RolEjercicioModel(Base):
    __tablename__ = "rol_ejercicio"

    codigo: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))


class EscenarioModel(Base):
    __tablename__ = "escenario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo_codigo: Mapped[str] = mapped_column(
        String(40), ForeignKey("tipo_escenario.codigo"), index=True
    )
    descripcion: Mapped[str] = mapped_column(Text)
    nivel: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(15), index=True)
    es_base: Mapped[bool] = mapped_column(Boolean)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[RolEjercicioModel]] = relationship(secondary=escenario_rol)
    injects: Mapped[list["InjectModel"]] = relationship(
        cascade="all, delete-orphan", order_by="InjectModel.orden"
    )
    tareas: Mapped[list["TareaModel"]] = relationship(
        cascade="all, delete-orphan", order_by="TareaModel.posicion"
    )


class InjectModel(Base):
    __tablename__ = "inject"
    __table_args__ = (UniqueConstraint("escenario_id", "orden"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    escenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("escenario.id", ondelete="CASCADE"), index=True
    )
    orden: Mapped[int] = mapped_column(SmallInteger)
    titulo: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str] = mapped_column(Text)
    minuto_sugerido: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class TareaModel(Base):
    __tablename__ = "tarea"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    escenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("escenario.id", ondelete="CASCADE"), index=True
    )
    posicion: Mapped[int] = mapped_column(SmallInteger)
    rol_codigo: Mapped[str] = mapped_column(
        String(40), ForeignKey("rol_ejercicio.codigo"), index=True
    )
    enunciado: Mapped[str] = mapped_column(Text)
    dificultad: Mapped[str] = mapped_column(String(10), index=True)
    criterios: Mapped[list[str]] = mapped_column(JSON)
    puntaje_maximo: Mapped[int] = mapped_column(SmallInteger)
    tiempo_limite_segundos: Mapped[int] = mapped_column(Integer)
    respuesta_esperada: Mapped[str | None] = mapped_column(Text, nullable=True)
