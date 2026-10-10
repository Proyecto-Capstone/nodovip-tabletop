"""Puerto de salida para persistir usuarios.

El dominio y los casos de uso dependen de esta interfaz, nunca de SQLAlchemy.
La implementación concreta vive en adapters/outbound/persistence.
"""

from typing import Protocol
from uuid import UUID

from app.domain.usuarios import Usuario


class UsuarioRepository(Protocol):
    def obtener_por_id(self, usuario_id: UUID) -> Usuario | None: ...

    def obtener_por_correo(self, correo: str) -> Usuario | None: ...

    def listar(self) -> list[Usuario]: ...

    def guardar(self, usuario: Usuario) -> Usuario: ...
