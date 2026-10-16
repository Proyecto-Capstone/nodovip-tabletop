"""Implementación SQLAlchemy del historial de accesos (adaptador de salida)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models_accesos import AccesoModel
from app.domain.autenticacion import RegistroAcceso, ResultadoAcceso
from app.ports.autenticacion import FiltroAccesos


def _a_dominio(m: AccesoModel) -> RegistroAcceso:
    return RegistroAcceso(
        id=m.id,
        usuario_id=m.usuario_id,
        correo=m.correo_ingresado,
        fecha_hora=m.fecha_hora,
        ip=m.ip,
        user_agent=m.user_agent,
        resultado=ResultadoAcceso(m.resultado),
    )


class SqlRegistroAccesoRepository:
    def __init__(self, session: Session):
        self.session = session

    def registrar(self, registro: RegistroAcceso) -> None:
        modelo = AccesoModel(
            usuario_id=registro.usuario_id,
            correo_ingresado=registro.correo,
            ip=registro.ip,
            user_agent=registro.user_agent,
            resultado=registro.resultado.value,
        )
        if registro.fecha_hora is not None:
            modelo.fecha_hora = registro.fecha_hora
        self.session.add(modelo)
        self.session.commit()

    def resultados_recientes(
        self, correo: str, desde: datetime, limite: int
    ) -> list[ResultadoAcceso]:
        q = (
            select(AccesoModel.resultado)
            .where(
                AccesoModel.correo_ingresado == correo,
                AccesoModel.fecha_hora >= desde,
                AccesoModel.resultado != ResultadoAcceso.BLOQUEADO.value,
            )
            .order_by(AccesoModel.fecha_hora.desc(), AccesoModel.id.desc())
            .limit(limite)
        )
        return [ResultadoAcceso(r) for r in self.session.scalars(q)]

    def listar(self, filtro: FiltroAccesos) -> list[RegistroAcceso]:
        q = select(AccesoModel)
        if filtro.usuario_id:
            q = q.where(AccesoModel.usuario_id == filtro.usuario_id)
        if filtro.correo:
            q = q.where(AccesoModel.correo_ingresado.ilike(f"%{filtro.correo}%"))
        if filtro.resultado:
            q = q.where(AccesoModel.resultado == filtro.resultado.value)
        if filtro.desde:
            q = q.where(AccesoModel.fecha_hora >= filtro.desde)
        if filtro.hasta:
            q = q.where(AccesoModel.fecha_hora <= filtro.hasta)
        q = q.order_by(AccesoModel.fecha_hora.desc(), AccesoModel.id.desc()).limit(
            filtro.limite
        )
        return [_a_dominio(m) for m in self.session.scalars(q)]
