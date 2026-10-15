"""Reglas de autenticación e historial de accesos (PB-01, RNF-01).

Núcleo de dominio: no depende de FastAPI, SQLAlchemy, bcrypt ni JWT.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class ResultadoAcceso(StrEnum):
    EXITOSO = "exitoso"
    CREDENCIALES_INVALIDAS = "credenciales_invalidas"
    USUARIO_INACTIVO = "usuario_inactivo"
    BLOQUEADO = "bloqueado"


# Intentos que cuentan como fallo para el bloqueo por fuerza bruta.
RESULTADOS_FALLIDOS = frozenset(
    {ResultadoAcceso.CREDENCIALES_INVALIDAS, ResultadoAcceso.USUARIO_INACTIVO}
)

MAX_INTENTOS_FALLIDOS = 5
VENTANA_BLOQUEO = timedelta(minutes=15)


@dataclass
class RegistroAcceso:
    """Una fila del historial: cada intento de login, exitoso o no."""

    correo: str
    resultado: ResultadoAcceso
    ip: str
    usuario_id: UUID | None = None
    user_agent: str | None = None
    fecha_hora: datetime | None = None
    id: int | None = None


def fallos_consecutivos(resultados_recientes: Iterable[ResultadoAcceso]) -> int:
    """Cuenta los fallos desde el último acceso exitoso.

    Recibe los resultados del más reciente al más antiguo. Los intentos
    `bloqueado` no suman: así el bloqueo se levanta al cumplirse la ventana
    desde el 5.º fallo aunque se siga intentando mientras dura.
    """
    fallos = 0
    for resultado in resultados_recientes:
        if resultado == ResultadoAcceso.EXITOSO:
            break
        if resultado in RESULTADOS_FALLIDOS:
            fallos += 1
    return fallos


def esta_bloqueado(resultados_recientes: Iterable[ResultadoAcceso]) -> bool:
    return fallos_consecutivos(resultados_recientes) >= MAX_INTENTOS_FALLIDOS
