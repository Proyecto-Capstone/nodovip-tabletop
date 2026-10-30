"""Configuración común de las pruebas.

`sesion_por_cabecera` reemplaza la sesión real (cookie + JWT) por un usuario de
prueba cuyo rol viene en la cabecera `X-Rol-Prueba`. Existe SOLO en las
pruebas, para que las de escenarios y usuarios no tengan que iniciar sesión;
la autenticación real se prueba en test_api_autenticacion.py.
"""

import os
from typing import Annotated
from uuid import NAMESPACE_URL, uuid5

# Antes de importar la app: sin APP_ENV la configuración asume un servidor real.
os.environ.setdefault("APP_ENV", "test")

import pytest
from fastapi import Header, HTTPException, status

from app.adapters.inbound.api.reportes import get_tarea_reporte
from app.adapters.inbound.api.seguridad import (
    UsuarioActual,
    obtener_usuario_actual,
    obtener_usuario_ws,
)
from app.domain.usuarios import RolNombre
from app.main import app


def _usuario_por_cabecera(
    x_rol_prueba: Annotated[str | None, Header()] = None,
) -> UsuarioActual:
    try:
        rol = RolNombre(x_rol_prueba or "")
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado") from None
    return UsuarioActual(
        id=uuid5(NAMESPACE_URL, f"prueba:{rol}"),
        nombre=f"Prueba {rol}",
        correo=f"{rol}@prueba.test",
        rol=rol,
    )


def _usuario_ws_por_cabecera(
    x_rol_prueba: Annotated[str | None, Header()] = None,
) -> UsuarioActual | None:
    """Igual que _usuario_por_cabecera, para WebSocket: None si no hay rol."""
    try:
        return _usuario_por_cabecera(x_rol_prueba)
    except HTTPException:
        return None


@pytest.fixture
def sesion_por_cabecera():
    app.dependency_overrides[obtener_usuario_actual] = _usuario_por_cabecera
    app.dependency_overrides[obtener_usuario_ws] = _usuario_ws_por_cabecera
    yield
    app.dependency_overrides.pop(obtener_usuario_actual, None)
    app.dependency_overrides.pop(obtener_usuario_ws, None)


@pytest.fixture(autouse=True)
def sin_reporte_en_segundo_plano():
    """Cerrar una sesión genera el PDF en segundo plano con la BD real (PB-14).
    En las pruebas con dobles se reemplaza por una tarea vacía; las pruebas de
    reportes la vuelven a reemplazar si la necesitan."""
    app.dependency_overrides[get_tarea_reporte] = lambda: lambda sesion_id: None
    yield
    app.dependency_overrides.pop(get_tarea_reporte, None)
