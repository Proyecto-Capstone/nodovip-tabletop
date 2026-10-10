"""Usuario actual y control de permisos para los endpoints.

TEMPORAL hasta PB-01 (PC-12): todavía no hay login. Mientras tanto, en los
ambientes `local` y `test` el rol se toma de la cabecera `X-Rol-Debug`
(por ejemplo `X-Rol-Debug: administrador`). En cualquier otro ambiente se
responde 401 siempre.

PB-01 reemplaza `obtener_usuario_actual` por la validación del token. Los
endpoints no cambian: siguen usando `requiere_permiso(...)`.
"""

import os
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.domain.usuarios import PERMISOS_POR_ROL, PermisoCodigo, RolNombre

AMBIENTES_CON_ROL_DEBUG = {"local", "test"}


@dataclass(frozen=True)
class UsuarioActual:
    rol: RolNombre

    def puede(self, permiso: PermisoCodigo) -> bool:
        return permiso in PERMISOS_POR_ROL[self.rol]


def obtener_usuario_actual(
    x_rol_debug: Annotated[str | None, Header()] = None,
) -> UsuarioActual:
    no_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
    )
    if os.getenv("APP_ENV") not in AMBIENTES_CON_ROL_DEBUG or not x_rol_debug:
        raise no_autenticado
    try:
        return UsuarioActual(rol=RolNombre(x_rol_debug))
    except ValueError:
        raise no_autenticado from None


def requiere_permiso(permiso: PermisoCodigo):
    """Dependencia de FastAPI: 403 si el rol del usuario no tiene el permiso."""

    def _verificar(
        usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
    ) -> UsuarioActual:
        if not usuario.puede(permiso):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return usuario

    return _verificar
