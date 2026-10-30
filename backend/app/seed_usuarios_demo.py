"""Crea usuarios ficticios para probar el diseñador y las sesiones (PB-05 en adelante).

Uso: docker compose exec -e DEMO_CONTRASENA=... backend python -m app.seed_usuarios_demo

Un moderador, una observadora (PB-12: leaderboard) y cinco participantes con
correos @demo.nodovip.test. Todos usan la contraseña de DEMO_CONTRASENA (debe
cumplir la política de PB-02). Si un correo ya existe, se omite. No corre en
producción.
"""

import os
import sys

from sqlalchemy.orm import Session

from app import config
from app.adapters.outbound.persistence.database import get_engine
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.adapters.outbound.seguridad.bcrypt_hasher import BcryptHasher
from app.application.usuarios import CorreoDuplicado, ServicioUsuarios
from app.domain.usuarios import ReglaUsuarioError, RolNombre

# Datos ficticios (RNF-02): nombres inventados y dominio reservado .test.
USUARIOS = [
    ("Mónica Moderadora", "moderadora", RolNombre.MODERADOR),
    ("Olga Observadora", "observadora", RolNombre.OBSERVADOR),
    ("Pedro Morales", "pedro.morales", RolNombre.PARTICIPANTE),
    ("Carlos Ramírez", "carlos.ramirez", RolNombre.PARTICIPANTE),
    ("Pedro Suárez", "pedro.suarez", RolNombre.PARTICIPANTE),
    ("María Vásquez", "maria.vasquez", RolNombre.PARTICIPANTE),
    ("Ana López", "ana.lopez", RolNombre.PARTICIPANTE),
]


def main() -> None:
    if config.ambiente() == "production":
        sys.exit("No se crean usuarios demo en producción.")
    contrasena = os.getenv("DEMO_CONTRASENA", "")
    if not contrasena:
        sys.exit("Falta la variable DEMO_CONTRASENA.")
    with Session(get_engine()) as session:
        servicio = ServicioUsuarios(SqlUsuarioRepository(session), BcryptHasher())
        for nombre, usuario, rol in USUARIOS:
            correo = f"{usuario}@demo.nodovip.test"
            try:
                servicio.crear(nombre, correo, contrasena, rol)
                print(f"Creado: {correo} ({rol})")
            except CorreoDuplicado:
                print(f"Ya existe: {correo}")
            except ReglaUsuarioError as e:
                sys.exit("; ".join(e.errores))


if __name__ == "__main__":
    main()
