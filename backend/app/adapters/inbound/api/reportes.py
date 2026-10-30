"""Reporte de brechas de una sesión finalizada (PB-14, RF-07).

Permiso `reportes:ver` (Analista, Moderador y Administrador). El Moderador solo
ve sus sesiones; Analista y Administrador, cualquier sesión finalizada.

- `GET /api/reportes`: sesiones finalizadas visibles y el estado de su PDF.
- `GET /api/reportes/{id}`: contenido del reporte (la pantalla "Reporte de brechas").
- `GET /api/reportes/{id}/pdf`: descarga del PDF (si todavía no existe, se genera).
- `POST /api/reportes/{id}/regenerar`: vuelve a generar el PDF.

Al cerrar una sesión (`en_vivo.py`), `generar_reporte_en_segundo_plano` crea el
PDF después de responder al moderador: el motor en vivo no espera a WeasyPrint.
"""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.inbound.api.seguridad import UsuarioActual, requiere_permiso
from app.adapters.outbound.en_vivo import adaptador_en_vivo
from app.adapters.outbound.persistence.database import abrir_sesion, get_session
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.adapters.outbound.persistence.repositorio_reportes import (
    SqlReporteRepository,
)
from app.adapters.outbound.persistence.repositorio_respuestas import (
    SqlRespuestaRepository,
)
from app.adapters.outbound.persistence.repositorio_sesiones import SqlSesionRepository
from app.adapters.outbound.persistence.repositorio_usuarios import (
    SqlUsuarioRepository,
)
from app.adapters.outbound.reportes import GeneradorWeasyPrint
from app.application.reportes import ServicioReportes, SesionConReporte
from app.application.sesiones import SesionNoEncontrada
from app.domain.reportes import (
    Brecha,
    EstadoReporte,
    FilaPuntaje,
    Recomendacion,
    ReporteGuardado,
    ReporteSesion,
    RespuestaReporte,
    Severidad,
    TipoBrecha,
)
from app.domain.usuarios import PermisoCodigo

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reportes", tags=["reportes"])


def _servicio(session: Session) -> ServicioReportes:
    return ServicioReportes(
        SqlSesionRepository(session),
        SqlRespuestaRepository(session),
        SqlCatalogoRepository(session),
        SqlUsuarioRepository(session),
        SqlEscenarioRepository(session),
        adaptador_en_vivo(),
        SqlReporteRepository(session),
        GeneradorWeasyPrint(),
    )


def get_servicio_reportes(
    session: Annotated[Session, Depends(get_session)],
) -> ServicioReportes:
    return _servicio(session)


def generar_reporte_en_segundo_plano(sesion_id: UUID) -> None:
    """Tarea de fondo del cierre: abre su propia sesión de BD (el request ya
    terminó). Nunca lanza: si falla, queda en el log y se puede regenerar."""
    try:
        with abrir_sesion() as session:
            _servicio(session).generar_al_cerrar(sesion_id)
    except Exception:
        log.exception("Falló la tarea de reporte de la sesión %s", sesion_id)


def get_tarea_reporte():
    """Dependencia para que las pruebas reemplacen la tarea de fondo."""
    return generar_reporte_en_segundo_plano


Servicio = Annotated[ServicioReportes, Depends(get_servicio_reportes)]
Lector = Annotated[UsuarioActual, Depends(requiere_permiso(PermisoCodigo.REPORTES_VER))]


def _es_moderador(usuario: UsuarioActual) -> bool:
    # Mismo criterio que leaderboard y en vivo: por permiso, no por nombre de rol.
    return usuario.puede(PermisoCodigo.SESIONES_CONDUCIR)


def _manejar_errores(funcion):
    try:
        return funcion()
    except SesionNoEncontrada:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Reporte no disponible: la sesión no existe o no ha finalizado",
        ) from None


def _generando_pdf(funcion):
    """Si WeasyPrint falla, 503 con el motivo (queda registrado en el reporte)."""

    def con_manejo():
        try:
            return funcion()
        except SesionNoEncontrada:
            raise
        except Exception as e:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"No se pudo generar el PDF: {e}"[:300],
            ) from e

    return _manejar_errores(con_manejo)


# --- Esquemas de salida -------------------------------------------------------------


class EstadoReporteSalida(BaseModel):
    estado: EstadoReporte
    solicitado_en: datetime
    generado_en: datetime | None
    error: str | None

    @classmethod
    def desde(cls, r: ReporteGuardado | None) -> "EstadoReporteSalida | None":
        if r is None:
            return None
        return cls(
            estado=r.estado,
            solicitado_en=r.solicitado_en,
            generado_en=r.generado_en,
            error=r.error,
        )


class SesionReporteSalida(BaseModel):
    id: UUID
    nombre: str
    cliente: str | None
    finalizada_en: datetime | None
    participantes: int
    reporte: EstadoReporteSalida | None

    @classmethod
    def desde(cls, x: SesionConReporte) -> "SesionReporteSalida":
        return cls(
            id=x.sesion.id,
            nombre=x.sesion.nombre,
            cliente=x.sesion.cliente,
            finalizada_en=x.sesion.finalizada_en,
            participantes=len(x.sesion.participantes),
            reporte=EstadoReporteSalida.desde(x.reporte),
        )


class FilaPuntajeSalida(BaseModel):
    nombre: str
    detalle: str
    puntaje: float
    maximo: int
    porcentaje: float
    respondidas: int
    sin_responder: int

    @classmethod
    def desde(cls, f: FilaPuntaje) -> "FilaPuntajeSalida":
        return cls(**vars(f))


class BrechaSalida(BaseModel):
    participante: str
    rol_codigo: str
    rol_nombre: str
    tarea: str
    inject_orden: int
    tipo: TipoBrecha
    tipo_etiqueta: str
    severidad: Severidad
    porcentaje: float
    detalle: list[str]
    recurrente_en: int

    @classmethod
    def desde(cls, b: Brecha) -> "BrechaSalida":
        return cls(
            participante=b.participante,
            rol_codigo=b.rol_codigo,
            rol_nombre=b.rol_nombre,
            tarea=b.tarea,
            inject_orden=b.inject_orden,
            tipo=b.tipo,
            tipo_etiqueta=b.etiqueta_tipo,
            severidad=b.severidad,
            porcentaje=b.porcentaje,
            detalle=b.detalle,
            recurrente_en=b.recurrente_en,
        )


class RespuestaReporteSalida(BaseModel):
    recibida_en: datetime
    participante: str
    rol_nombre: str
    inject_orden: int
    tarea: str
    contenido: str
    puntaje: float
    puntaje_maximo: int
    ajustada: bool

    @classmethod
    def desde(cls, r: RespuestaReporte) -> "RespuestaReporteSalida":
        return cls(**vars(r))


class RecomendacionSalida(BaseModel):
    prioridad: Severidad
    rol_nombre: str
    texto: str
    recurrente: bool

    @classmethod
    def desde(cls, r: Recomendacion) -> "RecomendacionSalida":
        return cls(**vars(r))


class ReporteSalida(BaseModel):
    sesion_id: UUID
    nombre: str
    cliente: str | None
    escenario: str
    moderador: str
    iniciada_en: datetime | None
    finalizada_en: datetime | None
    duracion_segundos: int | None
    participantes: int
    injects_lanzados: int
    total_injects: int
    puntaje_total: float
    maximo_total: int
    porcentaje_total: float
    por_participante: list[FilaPuntajeSalida]
    por_rol: list[FilaPuntajeSalida]
    brechas: list[BrechaSalida]
    superadas: list[BrechaSalida]
    respuestas: list[RespuestaReporteSalida]
    recomendaciones: list[RecomendacionSalida]
    sesiones_anteriores: int
    pdf: EstadoReporteSalida | None

    @classmethod
    def desde(cls, r: ReporteSesion, pdf: ReporteGuardado | None) -> "ReporteSalida":
        return cls(
            sesion_id=r.sesion_id,
            nombre=r.nombre,
            cliente=r.cliente,
            escenario=r.escenario,
            moderador=r.moderador,
            iniciada_en=r.iniciada_en,
            finalizada_en=r.finalizada_en,
            duracion_segundos=r.duracion_segundos,
            participantes=r.participantes,
            injects_lanzados=r.injects_lanzados,
            total_injects=r.total_injects,
            puntaje_total=r.puntaje_total,
            maximo_total=r.maximo_total,
            porcentaje_total=r.porcentaje_total,
            por_participante=[FilaPuntajeSalida.desde(f) for f in r.por_participante],
            por_rol=[FilaPuntajeSalida.desde(f) for f in r.por_rol],
            brechas=[BrechaSalida.desde(b) for b in r.brechas],
            superadas=[BrechaSalida.desde(b) for b in r.superadas],
            respuestas=[RespuestaReporteSalida.desde(x) for x in r.respuestas],
            recomendaciones=[RecomendacionSalida.desde(x) for x in r.recomendaciones],
            sesiones_anteriores=r.sesiones_anteriores,
            pdf=EstadoReporteSalida.desde(pdf),
        )


# --- Endpoints ----------------------------------------------------------------------


@router.get("", response_model=list[SesionReporteSalida])
def reportes(servicio: Servicio, usuario: Lector):
    """Sesiones finalizadas visibles, la más reciente primero."""
    return [
        SesionReporteSalida.desde(x)
        for x in servicio.visibles(usuario.id, _es_moderador(usuario))
    ]


@router.get("/{sesion_id}", response_model=ReporteSalida)
def reporte(sesion_id: UUID, servicio: Servicio, usuario: Lector):
    es_moderador = _es_moderador(usuario)
    contenido = _manejar_errores(
        lambda: servicio.contenido(sesion_id, usuario.id, es_moderador)
    )
    return ReporteSalida.desde(
        contenido, servicio.estado(sesion_id, usuario.id, es_moderador)
    )


@router.get("/{sesion_id}/pdf")
def descargar_pdf(sesion_id: UUID, servicio: Servicio, usuario: Lector):
    pdf = _generando_pdf(
        lambda: servicio.pdf(sesion_id, usuario.id, _es_moderador(usuario))
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="reporte-brechas-{sesion_id}.pdf"'
        },
    )


@router.post("/{sesion_id}/regenerar", response_model=EstadoReporteSalida)
def regenerar(sesion_id: UUID, servicio: Servicio, usuario: Lector):
    """Vuelve a generar el PDF; por ejemplo, después de ajustar puntajes."""
    guardado = _generando_pdf(
        lambda: servicio.regenerar(sesion_id, usuario.id, _es_moderador(usuario))
    )
    return EstadoReporteSalida.desde(guardado)
