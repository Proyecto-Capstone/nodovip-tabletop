"""Endpoints REST del diseñador de tabletop (PB-05, RF-01) e invitaciones (PB-06).

Solo el Moderador (permiso `sesiones:disenar`) y solo sobre sus sesiones.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import config
from app.adapters.inbound.api.schemas_sesiones import (
    ParticipanteDisponible,
    SesionDetalle,
    SesionDiseno,
    SesionNueva,
    SesionResumen,
)
from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.correo import crear_enviador
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import (
    SqlSesionRepository,
)
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.invitaciones import ServicioInvitaciones
from app.application.sesiones import ServicioSesiones, SesionNoEncontrada
from app.domain.sesiones import ReglaSesionError
from app.domain.usuarios import PermisoCodigo

router = APIRouter(prefix="/api/sesiones", tags=["sesiones"])


def get_servicio(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioSesiones:
    repo = SqlSesionRepository(session)
    catalogo = SqlCatalogoRepository(session)
    usuarios = SqlUsuarioRepository(session)
    invitaciones = ServicioInvitaciones(
        repo, catalogo, usuarios, crear_enviador(), config.url_aplicacion()
    )
    return ServicioSesiones(
        repo,
        SqlEscenarioRepository(session),
        catalogo,
        usuarios,
        invitar=invitaciones.enviar_pendientes,
    )


Servicio = Annotated[ServicioSesiones, Depends(get_servicio)]
Disenador = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_DISENAR))
]


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada") from None
    except ReglaSesionError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e


# Va antes de /{sesion_id} para que la ruta no se lea como un id.
@router.get("/participantes-disponibles", response_model=list[ParticipanteDisponible])
def participantes_disponibles(servicio: Servicio, _: Disenador):
    return [
        ParticipanteDisponible.desde(u) for u in servicio.participantes_disponibles()
    ]


@router.get("", response_model=list[SesionResumen])
def listar_sesiones(servicio: Servicio, usuario: Disenador):
    return [SesionResumen.desde(s) for s in servicio.listar(usuario.id)]


@router.post("", response_model=SesionDetalle, status_code=status.HTTP_201_CREATED)
def crear_sesion(datos: SesionNueva, servicio: Servicio, usuario: Disenador):
    sesion = _manejar_errores(
        lambda: servicio.crear(
            datos.escenario_id, usuario.id, datos.nombre, datos.cliente
        )
    )
    return SesionDetalle.desde(sesion, servicio.reloj())


@router.get("/{sesion_id}", response_model=SesionDetalle)
def obtener_sesion(sesion_id: UUID, servicio: Servicio, usuario: Disenador):
    sesion = _manejar_errores(lambda: servicio.obtener(sesion_id, usuario.id))
    return SesionDetalle.desde(sesion, servicio.reloj())


@router.put("/{sesion_id}", response_model=SesionDetalle)
def guardar_diseno(
    sesion_id: UUID, datos: SesionDiseno, servicio: Servicio, usuario: Disenador
):
    def guardar():
        actual = servicio.obtener(sesion_id, usuario.id)
        return servicio.actualizar(sesion_id, usuario.id, datos.a_dominio(actual))

    sesion = _manejar_errores(guardar)
    return SesionDetalle.desde(sesion, servicio.reloj())


@router.post("/{sesion_id}/programar", response_model=SesionDetalle)
def programar_sesion(sesion_id: UUID, servicio: Servicio, usuario: Disenador):
    """Programa la sesión y envía las invitaciones por correo."""
    sesion = _manejar_errores(lambda: servicio.programar(sesion_id, usuario.id))
    return SesionDetalle.desde(sesion, servicio.reloj())


@router.post("/{sesion_id}/invitaciones", response_model=SesionDetalle)
def enviar_invitaciones(sesion_id: UUID, servicio: Servicio, usuario: Disenador):
    """Paso 6: reenvía las invitaciones pendientes o que fallaron."""
    sesion = _manejar_errores(
        lambda: servicio.enviar_invitaciones(sesion_id, usuario.id)
    )
    return SesionDetalle.desde(sesion, servicio.reloj())


@router.delete("/{sesion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_sesion(sesion_id: UUID, servicio: Servicio, usuario: Disenador):
    _manejar_errores(lambda: servicio.eliminar(sesion_id, usuario.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
