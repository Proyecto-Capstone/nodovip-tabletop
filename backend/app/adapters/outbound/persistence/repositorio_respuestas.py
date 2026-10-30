"""Implementación SQLAlchemy del puerto de respuestas (adaptador de salida)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_respuestas import (
    AjustePuntajeModel,
    RespuestaModel,
)
from app.domain.evaluacion import AjustePuntaje, Evaluacion
from app.domain.respuestas import Respuesta
from app.ports.respuesta_repository import RespuestaDuplicada


def _evaluacion(m: RespuestaModel) -> Evaluacion | None:
    if m.puntaje_automatico is None:
        return None
    detalle = m.eval_detalle or {}
    return Evaluacion(
        puntaje=float(m.puntaje_automatico),
        puntaje_maximo=m.puntaje_maximo or 0,
        completitud=float(m.eval_completitud or 0),
        precision=float(m.eval_precision or 0),
        tiempo=float(m.eval_tiempo or 0),
        aciertos=list(detalle.get("aciertos", [])),
        faltantes=list(detalle.get("faltantes", [])),
        errores=list(detalle.get("errores", [])),
    )


def _ajuste(m: AjustePuntajeModel) -> AjustePuntaje:
    return AjustePuntaje(
        id=m.id,
        respuesta_id=m.respuesta_id,
        moderador_id=m.moderador_id,
        puntaje_anterior=float(m.puntaje_anterior),
        puntaje_nuevo=float(m.puntaje_nuevo),
        motivo=m.motivo,
        creado_en=m.creado_en,
    )


def _a_dominio(m: RespuestaModel) -> Respuesta:
    return Respuesta(
        id=m.id,
        sesion_id=m.sesion_id,
        tarea_id=m.tarea_id,
        inject_id=m.inject_id,
        usuario_id=m.usuario_id,
        rol_codigo=m.rol_codigo,
        texto=m.texto,
        opciones_elegidas=list(m.opciones_elegidas),
        recibida_en=m.recibida_en,
        segundos_usados=m.segundos_usados,
        evaluacion=_evaluacion(m),
    )


class SqlRespuestaRepository:
    def __init__(self, session: Session):
        self.session = session

    def guardar(self, respuesta: Respuesta) -> Respuesta:
        """Solo inserta: una respuesta registrada no se modifica."""
        e = respuesta.evaluacion
        self.session.add(
            RespuestaModel(
                id=respuesta.id,
                sesion_id=respuesta.sesion_id,
                tarea_id=respuesta.tarea_id,
                inject_id=respuesta.inject_id,
                usuario_id=respuesta.usuario_id,
                rol_codigo=respuesta.rol_codigo,
                texto=respuesta.texto,
                opciones_elegidas=respuesta.opciones_elegidas,
                recibida_en=respuesta.recibida_en,
                segundos_usados=respuesta.segundos_usados,
                puntaje_automatico=e.puntaje if e else None,
                puntaje_maximo=e.puntaje_maximo if e else None,
                eval_completitud=e.completitud if e else None,
                eval_precision=e.precision if e else None,
                eval_tiempo=e.tiempo if e else None,
                eval_detalle={
                    "aciertos": e.aciertos,
                    "faltantes": e.faltantes,
                    "errores": e.errores,
                }
                if e
                else None,
            )
        )
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            if "uq_respuesta_tarea_usuario" in str(e.orig):
                raise RespuestaDuplicada(str(respuesta.tarea_id)) from e
            raise
        return respuesta

    def de_participante(self, sesion_id: UUID, usuario_id: UUID) -> list[Respuesta]:
        filas = self.session.scalars(
            select(RespuestaModel)
            .where(RespuestaModel.sesion_id == sesion_id)
            .where(RespuestaModel.usuario_id == usuario_id)
            .order_by(RespuestaModel.recibida_en)
        )
        return [_a_dominio(m) for m in filas]

    def de_sesion(self, sesion_id: UUID) -> list[Respuesta]:
        filas = self.session.scalars(
            select(RespuestaModel)
            .where(RespuestaModel.sesion_id == sesion_id)
            .order_by(RespuestaModel.recibida_en, RespuestaModel.id)
        )
        return [_a_dominio(m) for m in filas]

    def obtener(self, respuesta_id: UUID) -> Respuesta | None:
        m = self.session.get(RespuestaModel, respuesta_id)
        return _a_dominio(m) if m else None

    def agregar_ajuste(self, ajuste: AjustePuntaje, sesion_id: UUID) -> AjustePuntaje:
        """Solo inserta: los ajustes anteriores quedan como historial."""
        self.session.add(
            AjustePuntajeModel(
                id=ajuste.id,
                respuesta_id=ajuste.respuesta_id,
                sesion_id=sesion_id,
                moderador_id=ajuste.moderador_id,
                puntaje_anterior=ajuste.puntaje_anterior,
                puntaje_nuevo=ajuste.puntaje_nuevo,
                motivo=ajuste.motivo,
                creado_en=ajuste.creado_en,
            )
        )
        self.session.commit()
        return ajuste

    def ajustes_de_sesion(self, sesion_id: UUID) -> list[AjustePuntaje]:
        filas = self.session.scalars(
            select(AjustePuntajeModel)
            .where(AjustePuntajeModel.sesion_id == sesion_id)
            .order_by(AjustePuntajeModel.creado_en)
        )
        return [_ajuste(m) for m in filas]
