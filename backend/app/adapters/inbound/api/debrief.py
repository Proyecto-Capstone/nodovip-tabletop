"""Debrief de la sesión y resumen del participante (PC-45).

- `GET  /api/sesiones/{id}/debrief`: el debrief (permiso `reportes:ver`; el
  Moderador solo de sus sesiones). Si todavía no se empezó, `estado` es
  `sin_iniciar` y las listas vienen vacías.
- `PUT  /api/sesiones/{id}/debrief`: guarda el borrador (moderador dueño).
- `POST /api/sesiones/{id}/debrief/completar`: lo cierra y regenera el reporte
  PDF en segundo plano para que incluya las lecciones aprendidas.
- `POST /api/sesiones/{id}/debrief/reabrir`: vuelve a borrador.
- `GET  /api/mis-sesiones/{id}/resumen`: resumen personal del participante.

Solo para sesiones finalizadas: antes, 404.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.adapters.inbound.api.reportes import get_tarea_reporte
from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.en_vivo import adaptador_en_vivo
from app.adapters.outbound.persistence.database import get_session
from app.adapters.outbound.persistence.repositorio_debrief import SqlDebriefRepository
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
)
from app.adapters.outbound.persistence.repositorio_respuestas import (
    SqlRespuestaRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.application.debrief import (
    ResumenParticipante,
    ServicioDebrief,
    ServicioResumenParticipante,
    TareaResumen,
    VistaDebrief,
)
from app.application.sesiones import SesionNoEncontrada
from app.domain.debrief import (
    MAX_ELEMENTOS,
    AccionMejora,
    Debrief,
    PrioridadAccion,
    ReglaDebriefError,
)
from app.domain.sesiones import TipoTarea
from app.domain.usuarios import PermisoCodigo

router = APIRouter(tags=["debrief"])


def get_servicio_debrief(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioDebrief:
    return ServicioDebrief(
        SqlSesionRepository(session),
        SqlDebriefRepository(session),
        SqlCatalogoRepository(session),
    )


def get_servicio_resumen(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioResumenParticipante:
    return ServicioResumenParticipante(
        SqlSesionRepository(session),
        SqlRespuestaRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
        adaptador_en_vivo(),
        SqlDebriefRepository(session),
    )


Servicio = Annotated[ServicioDebrief, Depends(get_servicio_debrief)]
Resumenes = Annotated[ServicioResumenParticipante, Depends(get_servicio_resumen)]
Lector = Annotated[UsuarioActual, Depends(requiere_permiso(PermisoCodigo.REPORTES_VER))]
Conductor = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_CONDUCIR))
]
Participante = Annotated[
    UsuarioActual, Depends(requiere_permiso(PermisoCodigo.SESIONES_PARTICIPAR))
]
TareaReporte = Annotated[Callable[[UUID], None], Depends(get_tarea_reporte)]


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Debrief no disponible: la sesión no existe o no ha finalizado",
        ) from None
    except ReglaDebriefError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, {"errores": e.errores}
        ) from e


# --- Esquemas -----------------------------------------------------------------------


class AccionEsquema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    descripcion: str = Field(max_length=500)
    prioridad: PrioridadAccion = PrioridadAccion.MEDIA
    rol_codigo: str | None = Field(default=None, max_length=40)
    plazo: date | None = None

    def a_dominio(self) -> AccionMejora:
        return AccionMejora(
            descripcion=self.descripcion,
            prioridad=self.prioridad,
            rol_codigo=self.rol_codigo or None,
            plazo=self.plazo,
        )


class DebriefEntrada(BaseModel):
    fortalezas: list[str] = Field(default_factory=list, max_length=MAX_ELEMENTOS)
    mejoras: list[str] = Field(default_factory=list, max_length=MAX_ELEMENTOS)
    acciones: list[AccionEsquema] = Field(
        default_factory=list, max_length=MAX_ELEMENTOS
    )


class AccionSalida(AccionEsquema):
    responsable: str


def _acciones(d: Debrief, roles: dict[str, str]) -> list[AccionSalida]:
    return [
        AccionSalida(
            descripcion=a.descripcion,
            prioridad=a.prioridad,
            rol_codigo=a.rol_codigo,
            plazo=a.plazo,
            responsable=roles.get(a.rol_codigo, a.rol_codigo)
            if a.rol_codigo
            else "Toda la organización",
        )
        for a in d.acciones
    ]


class RolSalida(BaseModel):
    codigo: str
    nombre: str


class DebriefSalida(BaseModel):
    sesion_id: UUID
    sesion_nombre: str
    cliente: str | None
    finalizada_en: datetime | None
    estado: Literal["sin_iniciar", "borrador", "completado"]
    fortalezas: list[str]
    mejoras: list[str]
    acciones: list[AccionSalida]
    actualizado_en: datetime | None
    completado_en: datetime | None
    puede_editar: bool
    # Roles de la sesión, para elegir el responsable de cada acción.
    roles: list[RolSalida]

    @classmethod
    def desde(cls, v: VistaDebrief) -> "DebriefSalida":
        d = v.debrief
        return cls(
            sesion_id=v.sesion.id,
            sesion_nombre=v.sesion.nombre,
            cliente=v.sesion.cliente,
            finalizada_en=v.sesion.finalizada_en,
            estado=d.estado.value if d else "sin_iniciar",
            fortalezas=d.fortalezas if d else [],
            mejoras=d.mejoras if d else [],
            acciones=_acciones(d, v.roles) if d else [],
            actualizado_en=d.actualizado_en if d else None,
            completado_en=d.completado_en if d else None,
            puede_editar=v.puede_editar,
            roles=[RolSalida(codigo=c, nombre=n) for c, n in v.roles.items()],
        )


class LeccionesSalida(BaseModel):
    """Las lecciones de un debrief completado, tal como las ve el participante."""

    fortalezas: list[str]
    mejoras: list[str]
    acciones: list[AccionSalida]


class TareaResumenSalida(BaseModel):
    inject_orden: int
    inject_titulo: str
    enunciado: str
    tipo: TipoTarea
    puntaje_maximo: int
    respondida: bool
    respuesta: str | None
    puntaje: float
    aciertos: list[str]
    faltantes: list[str]
    errores: list[str]
    opciones_correctas: list[str]
    ajuste_motivo: str | None

    @classmethod
    def desde(cls, t: TareaResumen) -> "TareaResumenSalida":
        return cls(**vars(t))


class ResumenSalida(BaseModel):
    sesion_id: UUID
    nombre: str
    finalizada_en: datetime | None
    rol_nombre: str
    puntaje: float
    maximo: int
    porcentaje: float
    posicion: int
    total_participantes: int
    tareas: list[TareaResumenSalida]
    lecciones: LeccionesSalida | None

    @classmethod
    def desde(cls, r: ResumenParticipante) -> "ResumenSalida":
        return cls(
            sesion_id=r.sesion.id,
            nombre=r.sesion.nombre,
            finalizada_en=r.sesion.finalizada_en,
            rol_nombre=r.rol_nombre,
            puntaje=r.puntaje,
            maximo=r.maximo,
            porcentaje=r.porcentaje,
            posicion=r.posicion,
            total_participantes=r.total_participantes,
            tareas=[TareaResumenSalida.desde(t) for t in r.tareas],
            lecciones=LeccionesSalida(
                fortalezas=r.debrief.fortalezas,
                mejoras=r.debrief.mejoras,
                acciones=_acciones(r.debrief, r.roles),
            )
            if r.debrief
            else None,
        )


# --- Endpoints ----------------------------------------------------------------------

BASE = "/api/sesiones/{sesion_id}/debrief"


def _es_moderador(usuario: UsuarioActual) -> bool:
    return usuario.puede(PermisoCodigo.SESIONES_CONDUCIR)


@router.get(BASE, response_model=DebriefSalida)
def ver_debrief(sesion_id: UUID, servicio: Servicio, usuario: Lector):
    vista = _manejar_errores(
        lambda: servicio.ver(sesion_id, usuario.id, _es_moderador(usuario))
    )
    return DebriefSalida.desde(vista)


@router.put(BASE, response_model=DebriefSalida)
def guardar_debrief(
    sesion_id: UUID, datos: DebriefEntrada, servicio: Servicio, usuario: Conductor
):
    """Guarda el borrador. Se puede llamar las veces que haga falta."""
    vista = _manejar_errores(
        lambda: servicio.guardar(
            sesion_id,
            usuario.id,
            datos.fortalezas,
            datos.mejoras,
            [a.a_dominio() for a in datos.acciones],
        )
    )
    return DebriefSalida.desde(vista)


@router.post(f"{BASE}/completar", response_model=DebriefSalida)
def completar_debrief(
    sesion_id: UUID,
    servicio: Servicio,
    usuario: Conductor,
    tareas: BackgroundTasks,
    generar_reporte: TareaReporte,
):
    """Cierra el debrief y regenera el PDF con las lecciones aprendidas."""
    vista = _manejar_errores(lambda: servicio.completar(sesion_id, usuario.id))
    tareas.add_task(generar_reporte, sesion_id)
    return DebriefSalida.desde(vista)


@router.post(f"{BASE}/reabrir", response_model=DebriefSalida)
def reabrir_debrief(sesion_id: UUID, servicio: Servicio, usuario: Conductor):
    vista = _manejar_errores(lambda: servicio.reabrir(sesion_id, usuario.id))
    return DebriefSalida.desde(vista)


@router.get("/api/mis-sesiones/{sesion_id}/resumen", response_model=ResumenSalida)
def mi_resumen(sesion_id: UUID, servicio: Resumenes, usuario: Participante):
    """Resumen personal del participante cuando la sesión ya finalizó."""
    return ResumenSalida.desde(
        _manejar_errores(lambda: servicio.resumen(sesion_id, usuario.id))
    )
