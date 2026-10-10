"""Endpoints REST de la biblioteca de escenarios (PB-03 y PB-04)."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.adapters.inbound.api.schemas_escenarios import (
    EscenarioDetalle,
    EscenarioEntrada,
    EscenarioResumen,
    RolEjercicioSalida,
    TareaBancoSalida,
    TipoEscenarioSalida,
)
from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.application.escenarios import EscenarioNoEncontrado, ServicioEscenarios
from app.domain.escenarios import EstadoEscenario, Nivel, ReglaEscenarioError
from app.domain.usuarios import PermisoCodigo
from app.ports.escenario_repository import FiltroBanco, FiltroEscenarios

router = APIRouter(prefix="/api", tags=["escenarios"])

GESTIONAR = PermisoCodigo.ESCENARIOS_GESTIONAR
LEER = PermisoCodigo.ESCENARIOS_LEER


def get_servicio(
    session: Annotated[Session, Depends(get_session)],
) -> Iterator[ServicioEscenarios]:
    yield ServicioEscenarios(
        SqlEscenarioRepository(session), SqlCatalogoRepository(session)
    )


Servicio = Annotated[ServicioEscenarios, Depends(get_servicio)]
Lector = Annotated[UsuarioActual, Depends(requiere_permiso(LEER))]
Gestor = Annotated[UsuarioActual, Depends(requiere_permiso(GESTIONAR))]


def _manejar_errores(funcion):
    try:
        return funcion()
    except EscenarioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Escenario no encontrado"
        ) from None
    except ReglaEscenarioError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e


# --- Catálogos (Tabla 6 y roles organizacionales) -----------------------------


@router.get("/catalogos/tipos-escenario", response_model=list[TipoEscenarioSalida])
def listar_tipos(servicio: Servicio, _: Lector):
    return [TipoEscenarioSalida.desde(t) for t in servicio.catalogo.tipos_escenario()]


@router.get("/catalogos/roles-ejercicio", response_model=list[RolEjercicioSalida])
def listar_roles(servicio: Servicio, _: Lector):
    return [RolEjercicioSalida.desde(r) for r in servicio.catalogo.roles_ejercicio()]


# --- PB-04: biblioteca (Moderador y Administrador) ----------------------------


@router.get("/escenarios", response_model=list[EscenarioResumen])
def listar_escenarios(
    servicio: Servicio,
    usuario: Lector,
    q: Annotated[str | None, Query(max_length=100)] = None,
    tipo: str | None = None,
    nivel: Nivel | None = None,
    rol: str | None = None,
    estado: Annotated[
        EstadoEscenario | None, Query(description="Solo para administradores")
    ] = None,
):
    filtro = FiltroEscenarios(
        texto=q,
        tipo_codigo=tipo,
        nivel=nivel,
        rol_codigo=rol,
        estados=[estado] if estado else None,
    )
    escenarios = servicio.listar(filtro, puede_gestionar=usuario.puede(GESTIONAR))
    return [EscenarioResumen.desde(e) for e in escenarios]


@router.get("/escenarios/{escenario_id}", response_model=EscenarioDetalle)
def obtener_escenario(escenario_id: UUID, servicio: Servicio, usuario: Lector):
    escenario = _manejar_errores(
        lambda: servicio.obtener(escenario_id, usuario.puede(GESTIONAR))
    )
    return EscenarioDetalle.desde(escenario)


@router.get("/banco-preguntas", response_model=list[TareaBancoSalida])
def banco_de_preguntas(
    servicio: Servicio,
    usuario: Lector,
    tipo: str | None = None,
    rol: str | None = None,
    dificultad: Nivel | None = None,
):
    puede_gestionar = usuario.puede(GESTIONAR)
    filtro = FiltroBanco(
        tipo_codigo=tipo,
        rol_codigo=rol,
        dificultad=dificultad,
        solo_publicados=not puede_gestionar,
    )
    resultado = servicio.banco_de_preguntas(filtro, puede_gestionar)
    return [TareaBancoSalida.desde(t) for t in resultado]


# --- PB-03: administración (solo Administrador) -------------------------------


@router.post(
    "/escenarios",
    response_model=EscenarioDetalle,
    status_code=status.HTTP_201_CREATED,
)
def crear_escenario(datos: EscenarioEntrada, servicio: Servicio, _: Gestor):
    escenario = _manejar_errores(lambda: servicio.crear(datos.a_dominio()))
    return EscenarioDetalle.desde(escenario)


@router.put("/escenarios/{escenario_id}", response_model=EscenarioDetalle)
def actualizar_escenario(
    escenario_id: UUID, datos: EscenarioEntrada, servicio: Servicio, _: Gestor
):
    escenario = _manejar_errores(
        lambda: servicio.actualizar(escenario_id, datos.a_dominio())
    )
    return EscenarioDetalle.desde(escenario)


@router.post("/escenarios/{escenario_id}/publicar", response_model=EscenarioDetalle)
def publicar_escenario(escenario_id: UUID, servicio: Servicio, _: Gestor):
    escenario = _manejar_errores(lambda: servicio.publicar(escenario_id))
    return EscenarioDetalle.desde(escenario)


@router.post("/escenarios/{escenario_id}/archivar", response_model=EscenarioDetalle)
def archivar_escenario(escenario_id: UUID, servicio: Servicio, _: Gestor):
    escenario = _manejar_errores(lambda: servicio.archivar(escenario_id))
    return EscenarioDetalle.desde(escenario)
