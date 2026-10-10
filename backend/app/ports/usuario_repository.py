"""Puertos de salida de la gestión de usuarios (M4).

El dominio y los casos de uso dependen de estas interfaces, nunca de SQLAlchemy
ni de bcrypt. Las implementaciones viven en adapters/outbound.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.usuarios import RolNombre, Usuario


@dataclass
class FiltroUsuarios:
    texto: str | None = None
    rol: RolNombre | None = None
    activo: bool | None = None


class UsuarioRepository(Protocol):
    def obtener_por_id(self, usuario_id: UUID) -> Usuario | None: ...

    def obtener_por_correo(self, correo: str) -> Usuario | None: ...

    def listar(self, filtro: FiltroUsuarios | None = None) -> list[Usuario]: ...

    def contar_activos(self, rol: RolNombre) -> int: ...

    def guardar(self, usuario: Usuario) -> Usuario: ...

    def eliminar(self, usuario_id: UUID) -> None: ...


class HasherContrasenas(Protocol):
    def hashear(self, contrasena: str) -> str: ...

    def verificar(self, contrasena: str, hash_guardado: str) -> bool: ...
