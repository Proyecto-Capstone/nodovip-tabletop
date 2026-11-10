"""Carga el catálogo de escenarios profesionales ficticios publicados (PC-46).

Uso:
    docker compose exec backend python -m app.seed_escenarios
    docker compose exec backend python -m app.seed_escenarios --actualizar

Es idempotente: un escenario que ya existe (mismo nombre) no se duplica. Con
`--actualizar` se reemplaza su contenido por el del catálogo; las sesiones ya
creadas no cambian porque copiaron el contenido al crearse. Todo es ficticio,
sin datos reales de clientes de NODOVIP.
"""

import sys
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.database import get_engine
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.application.escenarios import ServicioEscenarios
from app.catalogo_escenarios import CATALOGO
from app.catalogo_escenarios.ransomware import NOMBRE, escenario_ransomware
from app.domain.escenarios import EstadoEscenario
from app.ports.escenario_repository import FiltroEscenarios

# Se mantienen para quienes ya los importaban desde aquí (pruebas, scripts).
__all__ = ["NOMBRE", "cargar", "escenario_ransomware"]


@dataclass
class ResultadoCarga:
    creados: list[str]
    actualizados: list[str]
    sin_cambios: list[str]


def cargar(servicio: ServicioEscenarios, actualizar: bool = False) -> ResultadoCarga:
    """Crea y publica cada escenario del catálogo que falte."""
    resultado = ResultadoCarga([], [], [])
    for fabrica in CATALOGO:
        nuevo = fabrica()
        existentes = servicio.listar(
            FiltroEscenarios(texto=nuevo.nombre), puede_gestionar=True
        )
        actual = next((e for e in existentes if e.nombre == nuevo.nombre), None)
        if actual is None:
            creado = servicio.crear(nuevo)
            servicio.publicar(creado.id)
            resultado.creados.append(nuevo.nombre)
        elif actualizar:
            servicio.actualizar(actual.id, nuevo)
            if actual.estado != EstadoEscenario.PUBLICADO:
                servicio.publicar(actual.id)
            resultado.actualizados.append(nuevo.nombre)
        else:
            resultado.sin_cambios.append(nuevo.nombre)
    return resultado


def main() -> None:
    actualizar = "--actualizar" in sys.argv[1:]
    with Session(get_engine()) as session:
        servicio = ServicioEscenarios(
            SqlEscenarioRepository(session), SqlCatalogoRepository(session)
        )
        r = cargar(servicio, actualizar)
    for nombre in r.creados:
        print(f"Publicado: {nombre}")
    for nombre in r.actualizados:
        print(f"Actualizado: {nombre}")
    for nombre in r.sin_cambios:
        print(f"Ya existe (usa --actualizar para reemplazarlo): {nombre}")


if __name__ == "__main__":
    main()
