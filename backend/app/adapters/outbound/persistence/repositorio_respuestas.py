"""Implementación SQLAlchemy del puerto de respuestas (adaptador de salida)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_respuestas import RespuestaModel
from app.domain.respuestas import Respuesta
from app.ports.respuesta_repository import RespuestaDuplicada


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
    )


class SqlRespuestaRepository:
    def __init__(self, session: Session):
        self.session = session

    def guardar(self, respuesta: Respuesta) -> Respuesta:
        """Solo inserta: una respuesta registrada no se modifica."""
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
