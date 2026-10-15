"""Configuración leída de variables de entorno.

Si `APP_ENV` no está definido se asume un ambiente real (no de desarrollo):
es la opción segura, porque exige `JWT_SECRETO` y cookies `Secure`.
"""

import os

AMBIENTES_DESARROLLO = {"local", "test"}
JWT_SECRETO_MIN = 32
# Solo para local y test. Nunca se usa en staging ni en la Demo.
_SECRETO_DESARROLLO = "secreto-solo-para-desarrollo-local-no-usar-en-servidores"


def ambiente() -> str:
    return os.getenv("APP_ENV", "production")


def es_desarrollo() -> bool:
    return ambiente() in AMBIENTES_DESARROLLO


def jwt_secreto() -> str:
    secreto = os.getenv("JWT_SECRETO", "")
    if secreto:
        if len(secreto) < JWT_SECRETO_MIN and not es_desarrollo():
            raise RuntimeError(
                f"JWT_SECRETO debe tener al menos {JWT_SECRETO_MIN} caracteres"
            )
        return secreto
    if es_desarrollo():
        return _SECRETO_DESARROLLO
    raise RuntimeError("Falta la variable de entorno JWT_SECRETO")


def cookie_segura() -> bool:
    """Cookie `Secure` (solo HTTPS). `COOKIE_SEGURA=false` la apaga si la VM aún
    no tiene HTTPS; por defecto va encendida fuera de local y test."""
    # docker-compose entrega "" cuando la variable no está en .env.
    valor = os.getenv("COOKIE_SEGURA", "").strip().lower()
    if valor:
        return valor in {"1", "true", "si", "sí", "yes"}
    return not es_desarrollo()


def verificar_configuracion() -> None:
    """Falla al arrancar si falta algo obligatorio, en vez de en el primer login."""
    jwt_secreto()
