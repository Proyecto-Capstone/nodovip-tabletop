"""Modelos ORM de usuarios, roles y permisos (adaptador de salida)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Table,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.outbound.persistence.database import Base

rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column(
        "rol_id",
        SmallInteger,
        ForeignKey("rol.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permiso_id",
        SmallInteger,
        ForeignKey("permiso.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class RolModel(Base):
    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)
    descripcion: Mapped[str] = mapped_column(String(255))

    permisos: Mapped[list["PermisoModel"]] = relationship(secondary=rol_permiso)


class PermisoModel(Base):
    __tablename__ = "permiso"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    descripcion: Mapped[str] = mapped_column(String(255))


class UsuarioModel(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    correo: Mapped[str] = mapped_column(String(255), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    rol_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("rol.id"), index=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    rol: Mapped[RolModel] = relationship()
