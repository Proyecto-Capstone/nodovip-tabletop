"""Historial de accesos (PB-01, RNF-01). Solo Administrador."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.adapters.inbound.api.seguridad import (
    UsuarioActual,
    get_servicio_autenticacion,
    requiere_permiso,
)
from app.application.autenticacion import ServicioAutenticacion
from app.domain.autenticacion import RegistroAcceso, ResultadoAcceso
from app.domain.usuarios import PermisoCodigo
from app.ports.autenticacion import FiltroAccesos

router = APIRouter(prefix="/api/accesos", tags=["accesos"])

Servicio = Annotated[ServicioAutenticacion, Depends(get_servicio_autenticacion)]
Administrador = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.USUARIOS_GESTIONAR))
]


class AccesoSalida(BaseModel):
    id: int
    fecha_hora: datetime | None
    correo: str
    usuario_id: UUID | None
    ip: str
    user_agent: str | None
    resultado: ResultadoAcceso

    @classmethod
    def desde(cls, r: RegistroAcceso) -> "AccesoSalida":
        return cls(
            id=r.id or 0,
            fecha_hora=r.fecha_hora,
            correo=r.correo,
            usuario_id=r.usuario_id,
            ip=r.ip,
            user_agent=r.user_agent,
            resultado=r.resultado,
        )


@router.get("", response_model=list[AccesoSalida])
def listar_accesos(
    servicio: Servicio,
    _: Administrador,
    usuario_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    resultado: ResultadoAcceso | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limite: Annotated[int, Query(ge=1, le=1000)] = 200,
):
    filtro = FiltroAccesos(
        usuario_id=usuario_id,
        correo=q or None,
        resultado=resultado,
        desde=desde,
        hasta=hasta,
        limite=limite,
    )
    return [AccesoSalida.desde(r) for r in servicio.listar_accesos(filtro)]
