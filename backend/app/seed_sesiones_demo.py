"""Crea sesiones programadas de ejemplo para probar el monitoreo (PC-24).

Uso: docker compose exec backend python -m app.seed_sesiones_demo [cantidad]

Requiere que ya existan los usuarios demo (app.seed_usuarios_demo) y el
escenario demo publicado (app.seed_escenarios): este script no los crea,
para no duplicar esa lógica.

Crea `cantidad` (10 por defecto, el mismo valor que
MAX_SESIONES_ACTIVAS_POR_DEFECTO) sesiones PROGRAMADA del escenario demo,
con la moderadora demo y los cinco participantes demo repartidos uno por
rol, listas para arrancarse a mano y así probar el panel de monitoreo (y
su límite configurable) con varias sesiones en_curso a la vez. Es
idempotente: si ya existe una sesión con el mismo nombre para la
moderadora demo, se omite. No corre en producción.
"""

import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app import config
from app.adapters.outbound.persistence.database import get_engine
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.sesiones import ServicioSesiones
from app.domain.escenarios import EstadoEscenario
from app.domain.sesiones import MAX_SESIONES_ACTIVAS_POR_DEFECTO, ParticipanteSesion
from app.domain.usuarios import RolNombre
from app.ports.escenario_repository import FiltroEscenarios
from app.ports.usuario_repository import FiltroUsuarios
from app.seed_escenarios import NOMBRE as NOMBRE_ESCENARIO_DEMO
from app.seed_usuarios_demo import USUARIOS as USUARIOS_DEMO

CANTIDAD_POR_DEFECTO = MAX_SESIONES_ACTIVAS_POR_DEFECTO
_, _MODERADORA_USUARIO, _ = next(
    u for u in USUARIOS_DEMO if u[2] == RolNombre.MODERADOR
)
MODERADORA_DEMO = f"{_MODERADORA_USUARIO}@demo.nodovip.test"


def main() -> None:
    if config.ambiente() == "production":
        sys.exit("No se crean sesiones demo en producción.")
    cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else CANTIDAD_POR_DEFECTO

    with Session(get_engine()) as session:
        usuarios = SqlUsuarioRepository(session)
        escenarios = SqlEscenarioRepository(session)
        catalogo = SqlCatalogoRepository(session)

        moderadora = usuarios.obtener_por_correo(MODERADORA_DEMO)
        if moderadora is None:
            sys.exit(
                "Falta la moderadora demo: corre primero "
                "python -m app.seed_usuarios_demo."
            )
        participantes = usuarios.listar(
            FiltroUsuarios(rol=RolNombre.PARTICIPANTE, activo=True)
        )
        candidatos = escenarios.listar(
            FiltroEscenarios(
                texto=NOMBRE_ESCENARIO_DEMO, estados=[EstadoEscenario.PUBLICADO]
            )
        )
        escenario = next(
            (e for e in candidatos if e.nombre == NOMBRE_ESCENARIO_DEMO), None
        )
        if escenario is None:
            sys.exit(
                "Falta el escenario demo publicado: corre primero "
                "python -m app.seed_escenarios."
            )
        if len(participantes) < len(escenario.roles):
            sys.exit(
                f"Hacen falta {len(escenario.roles) - len(participantes)} "
                "participantes demo para cubrir los roles del escenario: corre "
                "primero python -m app.seed_usuarios_demo."
            )

        sesiones_app = ServicioSesiones(
            SqlSesionRepository(session), escenarios, catalogo, usuarios
        )
        existentes = {s.nombre for s in sesiones_app.listar(moderadora.id)}
        creadas = 0
        for i in range(cantidad):
            nombre = f"Simulacro demo {i + 1:02}"
            if nombre in existentes:
                print(f"Ya existe: {nombre}")
                continue
            sesion = sesiones_app.crear(escenario.id, moderadora.id, nombre)
            sesion.participantes = [
                ParticipanteSesion(p.id, rol)
                for p, rol in zip(participantes, escenario.roles, strict=False)
            ]
            sesion.fecha_programada = datetime.now(UTC) + timedelta(days=1)
            sesion.duracion_minutos = 60
            sesiones_app.actualizar(sesion.id, moderadora.id, sesion)
            sesiones_app.programar(sesion.id, moderadora.id)
            creadas += 1
            print(f"Creada: {nombre} ({sesion.id})")
        print(f"{creadas} sesión(es) nueva(s) de {cantidad} pedidas.")


if __name__ == "__main__":
    main()
