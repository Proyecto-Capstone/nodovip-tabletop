"""Crea el primer administrador del sistema.

Uso: docker compose exec backend python -m app.crear_admin

Pide nombre, correo y contraseña por consola (la contraseña no se muestra).
Sirve para el primer arranque de cada ambiente; después los usuarios se
gestionan desde el panel de administración.
"""

import getpass

from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.database import get_engine
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.adapters.outbound.seguridad.bcrypt_hasher import BcryptHasher
from app.application.usuarios import CorreoDuplicado, ServicioUsuarios
from app.domain.usuarios import ReglaUsuarioError, RolNombre


def main() -> None:
    nombre = input("Nombre completo: ").strip()
    correo = input("Correo: ").strip()
    contrasena = getpass.getpass("Contraseña: ")
    if contrasena != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.")
        return
    with Session(get_engine()) as session:
        servicio = ServicioUsuarios(SqlUsuarioRepository(session), BcryptHasher())
        try:
            usuario = servicio.crear(
                nombre, correo, contrasena, RolNombre.ADMINISTRADOR
            )
        except CorreoDuplicado:
            print(f"Ya existe un usuario con el correo {correo}.")
            return
        except ReglaUsuarioError as e:
            for error in e.errores:
                print(f"- {error}")
            return
    print(f"Administrador creado: {usuario.correo} ({usuario.id})")


if __name__ == "__main__":
    main()
