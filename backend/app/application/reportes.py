"""Reporte de cierre: puntajes, brechas, trazabilidad y recomendaciones (PB-14, RF-07).

- Se arma con lo que ya existe: el registro de respuestas (PB-09) y su puntaje
  vigente (PB-10). Las brechas y recomendaciones las calcula el dominio
  (`domain/reportes.py`).
- **Historial del cliente:** se comparan las sesiones finalizadas anteriores del
  mismo cliente (las 5 más recientes) para marcar brechas recurrentes y las
  que ya se superaron.
- **PDF:** lo genera el puerto `GeneradorPdf` (WeasyPrint). Al cerrar la sesión
  se genera en segundo plano y queda guardado; se puede regenerar.

Acceso (permiso `reportes:ver`): Analista y Administrador ven cualquier sesión
finalizada; el Moderador solo las suyas. Una sesión que no está finalizada es
"no encontrada": el reporte es de cierre.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.respuestas import RespuestaRegistrada, ServicioRegistroRespuestas
from app.application.sesiones import SesionNoEncontrada
from app.domain.evaluacion import sin_respuesta
from app.domain.reportes import (
    Brecha,
    EstadoReporte,
    FilaPuntaje,
    ReporteGuardado,
    ReporteSesion,
    RespuestaReporte,
    ResultadoTarea,
    detectar_brechas,
    marcar_recurrentes,
    recomendar,
    superadas,
)
from app.domain.sesiones import EstadoSesion, SesionTabletop
from app.ports.en_vivo import AlmacenEnVivo
from app.ports.escenario_repository import CatalogoRepository, EscenarioRepository
from app.ports.reportes import GeneradorPdf, ReporteRepository
from app.ports.respuesta_repository import RespuestaRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import UsuarioRepository

log = logging.getLogger(__name__)

# Sesiones anteriores del mismo cliente que se comparan.
MAX_HISTORIAL = 5


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class SesionConReporte:
    """Una sesión finalizada en la lista de reportes."""

    sesion: SesionTabletop
    reporte: ReporteGuardado | None


class ServicioReportes:
    def __init__(
        self,
        sesiones: SesionRepository,
        respuestas: RespuestaRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
        escenarios: EscenarioRepository,
        almacen: AlmacenEnVivo,
        reportes: ReporteRepository,
        generador: GeneradorPdf,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.sesiones = sesiones
        self.usuarios = usuarios
        self.escenarios = escenarios
        self.reportes = reportes
        self.generador = generador
        self.reloj = reloj
        self.registro = ServicioRegistroRespuestas(
            sesiones, respuestas, catalogo, usuarios, almacen, reloj
        )

    # --- Consultas ------------------------------------------------------------------

    def visibles(self, usuario_id: UUID, es_moderador: bool) -> list[SesionConReporte]:
        """Sesiones finalizadas con el estado de su PDF, la más reciente primero."""
        if es_moderador:
            sesiones = [
                s
                for s in self.sesiones.listar_por_moderador(usuario_id)
                if s.estado == EstadoSesion.FINALIZADA
            ]
        else:
            sesiones = self.sesiones.listar_por_estados((EstadoSesion.FINALIZADA,))
        sesiones.sort(key=lambda s: s.finalizada_en or datetime.min.replace(tzinfo=UTC))
        sesiones.reverse()
        estados = self.reportes.estados([s.id for s in sesiones])
        return [SesionConReporte(s, estados.get(s.id)) for s in sesiones]

    def contenido(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> ReporteSesion:
        return self._componer(self._visible(sesion_id, usuario_id, es_moderador))

    def estado(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> ReporteGuardado | None:
        self._visible(sesion_id, usuario_id, es_moderador)
        return self.reportes.obtener(sesion_id)

    # --- PDF --------------------------------------------------------------------------

    def pdf(self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool) -> bytes:
        """El PDF guardado; si todavía no existe (o falló), se genera ahora."""
        sesion = self._visible(sesion_id, usuario_id, es_moderador)
        guardado = self.reportes.obtener(sesion.id)
        if guardado and guardado.estado == EstadoReporte.GENERADO and guardado.pdf:
            return guardado.pdf
        return self._generar(sesion)

    def regenerar(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> ReporteGuardado:
        """Vuelve a generar el PDF (por ejemplo, después de ajustar puntajes)."""
        sesion = self._visible(sesion_id, usuario_id, es_moderador)
        self._generar(sesion)
        guardado = self.reportes.obtener(sesion.id)
        assert guardado is not None
        return guardado

    def generar_al_cerrar(self, sesion_id: UUID) -> None:
        """Lo llama el cierre de la sesión en segundo plano. Nunca lanza: un
        fallo queda registrado en el reporte y se puede regenerar después."""
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.estado != EstadoSesion.FINALIZADA:
            return
        try:
            self._generar(sesion)
        except Exception:
            log.exception("No se pudo generar el reporte de la sesión %s", sesion_id)

    def _generar(self, sesion: SesionTabletop) -> bytes:
        self.reportes.marcar_generando(sesion.id, self.reloj())
        try:
            pdf = self.generador.generar(self._componer(sesion))
        except Exception as e:
            self.reportes.marcar_fallido(sesion.id, str(e)[:500], self.reloj())
            raise
        self.reportes.guardar_pdf(sesion.id, pdf, self.reloj())
        return pdf

    # --- Composición ------------------------------------------------------------------

    def _visible(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> SesionTabletop:
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.estado != EstadoSesion.FINALIZADA:
            raise SesionNoEncontrada(str(sesion_id))
        if es_moderador and sesion.moderador_id != usuario_id:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion

    def _componer(self, sesion: SesionTabletop) -> ReporteSesion:
        registro = self.registro.registro_de(sesion)
        puntajes = self.registro.acumulado_de(sesion)
        anteriores = self._anteriores(sesion)
        historial = [self._brechas(s, self.registro.registro_de(s)) for s in anteriores]
        brechas = marcar_recurrentes(self._brechas(sesion, registro), historial)
        moderador = self.usuarios.obtener_por_id(sesion.moderador_id)
        escenario = self.escenarios.obtener(sesion.escenario_id)
        return ReporteSesion(
            sesion_id=sesion.id,
            nombre=sesion.nombre,
            cliente=sesion.cliente,
            escenario=escenario.nombre if escenario else "—",
            moderador=moderador.nombre if moderador else "—",
            iniciada_en=sesion.iniciada_en,
            finalizada_en=sesion.finalizada_en,
            participantes=len(sesion.participantes),
            injects_lanzados=sesion.inject_actual,
            total_injects=len(sesion.injects),
            puntaje_total=round(
                sum(p.acumulado.puntaje for p in puntajes.participantes), 2
            ),
            maximo_total=sum(p.acumulado.maximo for p in puntajes.participantes),
            por_participante=[
                FilaPuntaje(
                    nombre=p.nombre,
                    detalle=p.rol_nombre,
                    puntaje=p.acumulado.puntaje,
                    maximo=p.acumulado.maximo,
                    porcentaje=p.acumulado.porcentaje,
                    respondidas=p.acumulado.respondidas,
                    sin_responder=p.acumulado.sin_responder,
                )
                for p in puntajes.participantes
            ],
            por_rol=[
                FilaPuntaje(
                    nombre=r.rol_nombre,
                    detalle=f"{r.participantes} "
                    + ("participante" if r.participantes == 1 else "participantes"),
                    puntaje=r.acumulado.puntaje,
                    maximo=r.acumulado.maximo,
                    porcentaje=r.acumulado.porcentaje,
                    respondidas=r.acumulado.respondidas,
                    sin_responder=r.acumulado.sin_responder,
                )
                for r in sorted(puntajes.roles, key=lambda r: -r.acumulado.porcentaje)
            ],
            brechas=brechas,
            superadas=superadas(brechas, historial),
            respuestas=[_respuesta(r) for r in registro],
            recomendaciones=recomendar(brechas, len(anteriores)),
            sesiones_anteriores=len(anteriores),
            generado_en=self.reloj(),
        )

    def _anteriores(self, sesion: SesionTabletop) -> list[SesionTabletop]:
        """Sesiones finalizadas antes de esta, del mismo cliente (más reciente primero)."""
        if not sesion.cliente or sesion.finalizada_en is None:
            return []
        cliente = sesion.cliente.casefold()
        previas = [
            s
            for s in self.sesiones.listar_por_estados((EstadoSesion.FINALIZADA,))
            if s.id != sesion.id
            and s.cliente
            and s.cliente.casefold() == cliente
            and s.finalizada_en is not None
            and s.finalizada_en < sesion.finalizada_en
        ]
        previas.sort(key=lambda s: s.finalizada_en, reverse=True)  # type: ignore[arg-type, return-value]
        return previas[:MAX_HISTORIAL]

    def _brechas(
        self, sesion: SesionTabletop, registro: list[RespuestaRegistrada]
    ) -> list[Brecha]:
        """Una fila por participante y tarea lanzada de su rol (respondida o no)."""
        orden = {i.id: i.orden for i in sesion.injects}
        respuestas = {
            (r.respuesta.tarea_id, r.respuesta.usuario_id): r for r in registro
        }
        nombres_rol = {r.respuesta.rol_codigo: r.rol_nombre for r in registro}
        catalogo = self.registro.nombres_roles()
        resultados = []
        for p in sesion.participantes:
            nombre = self.registro.nombre_de(p.usuario_id)
            for t in sesion.tareas:
                inject = orden.get(t.inject_id)
                if t.rol_codigo != p.rol_codigo or inject is None:
                    continue
                if inject > sesion.inject_actual:
                    continue
                r = respuestas.get((t.id, p.usuario_id))
                evaluacion = r.evaluacion if r else sin_respuesta(t)
                resultados.append(
                    ResultadoTarea(
                        usuario_id=p.usuario_id,
                        participante=nombre,
                        rol_codigo=p.rol_codigo,
                        rol_nombre=nombres_rol.get(p.rol_codigo)
                        or catalogo.get(p.rol_codigo, p.rol_codigo),
                        tarea_id=t.id,
                        tarea=t.enunciado,
                        inject_orden=inject,
                        puntaje_maximo=t.puntaje_maximo,
                        puntaje=r.puntaje if r else None,
                        faltantes=list(evaluacion.faltantes),
                        errores=list(evaluacion.errores),
                    )
                )
        return detectar_brechas(resultados)


def _respuesta(r: RespuestaRegistrada) -> RespuestaReporte:
    contenido = r.respuesta.texto or ", ".join(r.opciones_elegidas_texto)
    return RespuestaReporte(
        recibida_en=r.respuesta.recibida_en,
        participante=r.participante_nombre,
        rol_nombre=r.rol_nombre,
        inject_orden=r.inject_orden,
        tarea=r.tarea.enunciado,
        contenido=contenido,
        puntaje=r.puntaje,
        puntaje_maximo=r.tarea.puntaje_maximo,
        ajustada=bool(r.ajustes),
    )
