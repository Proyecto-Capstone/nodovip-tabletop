"""Implementación SQLAlchemy del puerto de sesiones (adaptador de salida)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.adapters.outbound.persistence.models_escenarios import RolEjercicioModel
from app.adapters.outbound.persistence.models_sesiones import (
    SesionInjectModel,
    SesionModel,
    SesionParticipanteModel,
    SesionTareaModel,
)
from app.domain.escenarios import Inject, Nivel
from app.domain.sesiones import (
    ESTADOS_EDITABLES,
    EstadoInvitacion,
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    PesosPuntuacion,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)

# Clave arbitraria y fija para el advisory lock de pg_advisory_xact_lock
# (PC-24): cualquier bigint estable sirve, con tal de que todo el proceso
# use siempre el mismo valor para serializar los arranques de sesión.
_CLAVE_LOCK_LIMITE_SESIONES = 924_100_024


def _a_dominio(m: SesionModel) -> SesionTabletop:
    return SesionTabletop(
        id=m.id,
        nombre=m.nombre,
        escenario_id=m.escenario_id,
        moderador_id=m.moderador_id,
        estado=EstadoSesion(m.estado),
        roles=sorted(r.codigo for r in m.roles),
        injects=[
            Inject(
                id=i.id,
                orden=i.orden,
                titulo=i.titulo,
                descripcion=i.descripcion,
                minuto_sugerido=i.minuto_sugerido,
            )
            for i in m.injects
        ],
        tareas=[
            TareaSesion(
                id=t.id,
                inject_id=t.inject_id,
                rol_codigo=t.rol_codigo,
                tipo=TipoTarea(t.tipo),
                enunciado=t.enunciado,
                opciones=[OpcionRespuesta(**o) for o in t.opciones],
                criterios=list(t.criterios),
                dificultad=Nivel(t.dificultad),
                puntaje_maximo=t.puntaje_maximo,
                tiempo_limite_segundos=t.tiempo_limite_segundos,
                respuesta_esperada=t.respuesta_esperada,
            )
            for t in m.tareas
        ],
        participantes=sorted(
            (
                ParticipanteSesion(
                    usuario_id=p.usuario_id,
                    rol_codigo=p.rol_codigo,
                    invitacion=EstadoInvitacion(p.invitacion),
                    invitacion_enviada_en=p.invitacion_enviada_en,
                    invitacion_aceptada_en=p.invitacion_aceptada_en,
                    invitacion_error=p.invitacion_error,
                )
                for p in m.participantes
            ),
            key=lambda p: (p.rol_codigo, str(p.usuario_id)),
        ),
        pesos=PesosPuntuacion(m.peso_completitud, m.peso_precision, m.peso_tiempo),
        fecha_programada=m.fecha_programada,
        duracion_minutos=m.duracion_minutos,
        iniciada_en=m.iniciada_en,
        finalizada_en=m.finalizada_en,
        inject_actual=m.inject_actual,
    )


class SqlSesionRepository:
    def __init__(self, session: Session):
        self.session = session

    def _consulta(self):
        return select(SesionModel).options(
            selectinload(SesionModel.roles),
            selectinload(SesionModel.injects),
            selectinload(SesionModel.tareas),
            selectinload(SesionModel.participantes),
        )

    def obtener(self, sesion_id: UUID) -> SesionTabletop | None:
        modelo = self.session.scalar(
            self._consulta().where(SesionModel.id == sesion_id)
        )
        return _a_dominio(modelo) if modelo else None

    def listar_por_moderador(self, moderador_id: UUID) -> list[SesionTabletop]:
        q = (
            self._consulta()
            .where(SesionModel.moderador_id == moderador_id)
            .order_by(SesionModel.actualizado_en.desc())
        )
        return [_a_dominio(m) for m in self.session.scalars(q)]

    def liberar(self) -> None:
        """Devuelve la conexión al pool (el WebSocket la usa solo al empezar)."""
        self.session.close()

    def listar_por_participante(self, usuario_id: UUID) -> list[SesionTabletop]:
        q = self._consulta().where(
            SesionModel.participantes.any(
                SesionParticipanteModel.usuario_id == usuario_id
            )
        )
        return [_a_dominio(m) for m in self.session.scalars(q)]

    def listar_por_estados(
        self, estados: tuple[EstadoSesion, ...]
    ) -> list[SesionTabletop]:
        q = (
            self._consulta()
            .where(SesionModel.estado.in_([e.value for e in estados]))
            .order_by(SesionModel.actualizado_en.desc())
        )
        return [_a_dominio(m) for m in self.session.scalars(q)]

    def guardar(self, sesion: SesionTabletop) -> SesionTabletop:
        modelo = self.session.get(SesionModel, sesion.id)
        if modelo is None:
            modelo = SesionModel(id=sesion.id)
            self.session.add(modelo)
        modelo.nombre = sesion.nombre
        modelo.escenario_id = sesion.escenario_id
        modelo.moderador_id = sesion.moderador_id
        modelo.estado = sesion.estado.value
        modelo.fecha_programada = sesion.fecha_programada
        modelo.duracion_minutos = sesion.duracion_minutos
        modelo.iniciada_en = sesion.iniciada_en
        modelo.finalizada_en = sesion.finalizada_en
        modelo.inject_actual = sesion.inject_actual
        modelo.peso_completitud = sesion.pesos.completitud
        modelo.peso_precision = sesion.pesos.precision
        modelo.peso_tiempo = sesion.pesos.tiempo
        if sesion.estado in ESTADOS_EDITABLES or not modelo.tareas:
            self._reemplazar_contenido(modelo, sesion)
        else:
            self._actualizar_invitaciones(modelo, sesion)
        self.session.commit()
        return self.obtener(sesion.id)  # type: ignore[return-value]

    def iniciar_si_hay_cupo(
        self, sesion: SesionTabletop, maximo_activas: int
    ) -> SesionTabletop | None:
        """Cuenta las sesiones EN_CURSO y guarda en una sola transacción,
        serializada con un advisory lock (PC-24, RNF), para que dos
        arranques simultáneos nunca superen `maximo_activas`.

        Depende de que la sesión de SQLAlchemy esté en READ COMMITTED (el
        valor por defecto de PostgreSQL y de `database.py`, que no fija
        `isolation_level`): el conteo debe ver filas confirmadas *después*
        de tomar el lock, no la foto de antes de pedirlo. Con REPEATABLE
        READ el conteo vería el mismo snapshot que ya tenía esta
        transacción al leer `sesion` más arriba (p. ej. en
        `ServicioEnVivo.iniciar`), aunque otra transacción hubiera
        confirmado su "en_curso" mientras tanto — y se podría superar el
        máximo. Si alguna vez se cambia el nivel de aislamiento, el conteo
        tendría que hacerse con una consulta aparte que fuerce ver el
        estado ya confirmado tras el lock (por ejemplo, en su propia
        subtransacción).
        """
        self.session.execute(
            select(func.pg_advisory_xact_lock(_CLAVE_LOCK_LIMITE_SESIONES))
        )
        activas = self.session.scalar(
            select(func.count())
            .select_from(SesionModel)
            .where(SesionModel.estado == EstadoSesion.EN_CURSO.value)
        )
        if activas is not None and activas >= maximo_activas:
            # Libera el advisory lock (es de ámbito de transacción) sin
            # guardar nada.
            self.session.rollback()
            return None
        return self.guardar(sesion)

    @staticmethod
    def _actualizar_invitaciones(modelo: SesionModel, sesion: SesionTabletop) -> None:
        """Con el contenido fijo, solo cambia el seguimiento de las invitaciones
        (por ejemplo, alguien acepta con la sesión ya en curso)."""
        por_usuario = {p.usuario_id: p for p in sesion.participantes}
        for fila in modelo.participantes:
            p = por_usuario.get(fila.usuario_id)
            if p:
                fila.invitacion = p.invitacion.value
                fila.invitacion_enviada_en = p.invitacion_enviada_en
                fila.invitacion_aceptada_en = p.invitacion_aceptada_en
                fila.invitacion_error = p.invitacion_error

    def _reemplazar_contenido(
        self, modelo: SesionModel, sesion: SesionTabletop
    ) -> None:
        """Reescribe roles, injects, tareas y participantes del diseño.

        Solo mientras la sesión es editable: una vez en curso, las respuestas
        apuntan a sus tareas (PB-08/PB-09) y el contenido queda fijo.
        """
        modelo.roles = [
            self.session.get(RolEjercicioModel, codigo) for codigo in sesion.roles
        ]
        # Se reemplaza el contenido conservando los id. Primero las tareas,
        # que apuntan a los injects, y después los injects.
        modelo.tareas.clear()
        modelo.participantes.clear()
        self.session.flush()
        modelo.injects.clear()
        self.session.flush()
        modelo.injects = [
            SesionInjectModel(
                id=i.id,
                orden=i.orden,
                titulo=i.titulo,
                descripcion=i.descripcion,
                minuto_sugerido=i.minuto_sugerido,
            )
            for i in sesion.injects
        ]
        self.session.flush()
        modelo.tareas = [
            SesionTareaModel(
                id=t.id,
                posicion=pos,
                inject_id=t.inject_id,
                rol_codigo=t.rol_codigo,
                tipo=t.tipo.value,
                enunciado=t.enunciado,
                opciones=[
                    {"texto": o.texto, "correcta": o.correcta} for o in t.opciones
                ],
                criterios=t.criterios,
                dificultad=t.dificultad.value,
                puntaje_maximo=t.puntaje_maximo,
                tiempo_limite_segundos=t.tiempo_limite_segundos,
                respuesta_esperada=t.respuesta_esperada,
            )
            for pos, t in enumerate(sesion.tareas)
        ]
        modelo.participantes = [
            SesionParticipanteModel(
                usuario_id=p.usuario_id,
                rol_codigo=p.rol_codigo,
                invitacion=p.invitacion.value,
                invitacion_enviada_en=p.invitacion_enviada_en,
                invitacion_aceptada_en=p.invitacion_aceptada_en,
                invitacion_error=p.invitacion_error,
            )
            for p in sesion.participantes
        ]

    def eliminar(self, sesion_id: UUID) -> None:
        modelo = self.session.get(SesionModel, sesion_id)
        if modelo is not None:
            self.session.delete(modelo)
            self.session.commit()
