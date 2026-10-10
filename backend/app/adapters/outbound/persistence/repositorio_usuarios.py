"""Implementación SQLAlchemy del puerto de usuarios (adaptador de salida)."""

from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.adapters.outbound.persistence.models import RolModel, UsuarioModel
from app.domain.usuarios import RolNombre, Usuario
from app.ports.usuario_repository import FiltroUsuarios


def _a_dominio(m: UsuarioModel) -> Usuario:
    return Usuario(
        id=m.id,
        correo=m.correo,
        nombre=m.nombre,
        password_hash=m.password_hash,
        rol=RolNombre(m.rol.nombre),
        activo=m.activo,
        creado_en=m.creado_en,
    )


class SqlUsuarioRepository:
    def __init__(self, session: Session):
        self.session = session

    def _consulta(self):
        return select(UsuarioModel).options(joinedload(UsuarioModel.rol))

    def obtener_por_id(self, usuario_id: UUID) -> Usuario | None:
        modelo = self.session.scalar(
            self._consulta().where(UsuarioModel.id == usuario_id)
        )
        return _a_dominio(modelo) if modelo else None

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        modelo = self.session.scalar(
            self._consulta().where(func.lower(UsuarioModel.correo) == correo.lower())
        )
        return _a_dominio(modelo) if modelo else None

    def listar(self, filtro: FiltroUsuarios | None = None) -> list[Usuario]:
        filtro = filtro or FiltroUsuarios()
        q = self._consulta().join(UsuarioModel.rol)
        if filtro.texto:
            patron = f"%{filtro.texto}%"
            q = q.where(
                or_(
                    UsuarioModel.nombre.ilike(patron), UsuarioModel.correo.ilike(patron)
                )
            )
        if filtro.rol:
            q = q.where(RolModel.nombre == filtro.rol.value)
        if filtro.activo is not None:
            q = q.where(UsuarioModel.activo == filtro.activo)
        q = q.order_by(UsuarioModel.nombre)
        return [_a_dominio(m) for m in self.session.scalars(q)]

    def contar_activos(self, rol: RolNombre) -> int:
        q = (
            select(func.count())
            .select_from(UsuarioModel)
            .join(UsuarioModel.rol)
            .where(RolModel.nombre == rol.value, UsuarioModel.activo.is_(True))
        )
        return self.session.scalar(q) or 0

    def guardar(self, usuario: Usuario) -> Usuario:
        rol = self.session.scalar(
            select(RolModel).where(RolModel.nombre == usuario.rol)
        )
        if rol is None:
            raise LookupError(f"Rol no cargado en la base: {usuario.rol}")
        modelo = self.session.get(UsuarioModel, usuario.id)
        if modelo is None:
            modelo = UsuarioModel(id=usuario.id)
            self.session.add(modelo)
        modelo.correo = usuario.correo
        modelo.nombre = usuario.nombre
        modelo.password_hash = usuario.password_hash
        modelo.activo = usuario.activo
        modelo.rol_id = rol.id
        modelo.rol = rol
        self.session.commit()
        return self.obtener_por_id(usuario.id)  # type: ignore[return-value]

    def eliminar(self, usuario_id: UUID) -> None:
        try:
            self.session.execute(
                delete(UsuarioModel).where(UsuarioModel.id == usuario_id)
            )
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
