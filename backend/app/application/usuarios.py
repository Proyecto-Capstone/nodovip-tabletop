"""Casos de uso de la gestión de usuarios y roles (PB-02, RF-05).

Coordina dominio y puertos. No conoce HTTP, SQLAlchemy ni bcrypt.
"""

from uuid import UUID

from app.domain.usuarios import (
    ReglaUsuarioError,
    RolNombre,
    Usuario,
    normalizar_correo,
    validar_contrasena,
)
from app.ports.usuario_repository import (
    FiltroUsuarios,
    HasherContrasenas,
    UsuarioRepository,
)


class UsuarioNoEncontrado(LookupError):
    pass


class CorreoDuplicado(ValueError):
    pass


class ServicioUsuarios:
    def __init__(self, repo: UsuarioRepository, hasher: HasherContrasenas):
        self.repo = repo
        self.hasher = hasher

    def listar(self, filtro: FiltroUsuarios) -> list[Usuario]:
        return self.repo.listar(filtro)

    def obtener(self, usuario_id: UUID) -> Usuario:
        usuario = self.repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado(str(usuario_id))
        return usuario

    def crear(
        self, nombre: str, correo: str, contrasena: str, rol: RolNombre
    ) -> Usuario:
        correo = normalizar_correo(correo)
        self._verificar_correo_libre(correo)
        validar_contrasena(contrasena)
        usuario = Usuario(
            correo=correo,
            nombre=nombre.strip(),
            password_hash=self.hasher.hashear(contrasena),
            rol=rol,
        )
        return self.repo.guardar(usuario)

    def actualizar(
        self, usuario_id: UUID, nombre: str, correo: str, rol: RolNombre
    ) -> Usuario:
        usuario = self.obtener(usuario_id)
        correo = normalizar_correo(correo)
        if correo != usuario.correo:
            self._verificar_correo_libre(correo)
        if usuario.rol != rol:
            self._proteger_ultimo_administrador(usuario)
        usuario.nombre = nombre.strip()
        usuario.correo = correo
        usuario.rol = rol
        return self.repo.guardar(usuario)

    def desactivar(self, usuario_id: UUID) -> Usuario:
        usuario = self.obtener(usuario_id)
        if usuario.activo:
            self._proteger_ultimo_administrador(usuario)
            usuario.activo = False
            usuario = self.repo.guardar(usuario)
        return usuario

    def activar(self, usuario_id: UUID) -> Usuario:
        usuario = self.obtener(usuario_id)
        if not usuario.activo:
            usuario.activo = True
            usuario = self.repo.guardar(usuario)
        return usuario

    def restablecer_contrasena(self, usuario_id: UUID, contrasena: str) -> Usuario:
        usuario = self.obtener(usuario_id)
        validar_contrasena(contrasena)
        usuario.password_hash = self.hasher.hashear(contrasena)
        return self.repo.guardar(usuario)

    def eliminar(self, usuario_id: UUID) -> None:
        """Borrado definitivo. Solo para cuentas ya desactivadas.

        Si el usuario tiene registros asociados (accesos, sesiones, respuestas),
        la base de datos lo impide y el usuario debe quedar desactivado. Como
        todo login queda en el historial, en la práctica solo se eliminan
        cuentas que nunca ingresaron.
        """
        usuario = self.obtener(usuario_id)
        if usuario.activo:
            raise ReglaUsuarioError(
                ["Primero desactiva la cuenta; solo se eliminan cuentas inactivas"]
            )
        self.repo.eliminar(usuario_id)

    # --- reglas ----------------------------------------------------------------

    def _verificar_correo_libre(self, correo: str) -> None:
        if self.repo.obtener_por_correo(correo) is not None:
            raise CorreoDuplicado(correo)

    def _proteger_ultimo_administrador(self, usuario: Usuario) -> None:
        """El sistema nunca puede quedarse sin un administrador activo."""
        if (
            usuario.rol == RolNombre.ADMINISTRADOR
            and usuario.activo
            and self.repo.contar_activos(RolNombre.ADMINISTRADOR) <= 1
        ):
            raise ReglaUsuarioError(
                ["No se puede quitar ni desactivar al último administrador activo"]
            )
