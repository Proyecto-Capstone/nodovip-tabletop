"""Implementación SQLAlchemy de los puertos de escenarios (adaptador de salida)."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.adapters.outbound.persistence.models_escenarios import (
    EscenarioModel,
    InjectModel,
    RolEjercicioModel,
    TareaModel,
    TipoEscenarioModel,
)
from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    RolEjercicio,
    Tarea,
    TipoEscenario,
)
from app.ports.escenario_repository import (
    FiltroBanco,
    FiltroEscenarios,
    TareaDelBanco,
)


def _a_dominio(m: EscenarioModel) -> Escenario:
    return Escenario(
        id=m.id,
        nombre=m.nombre,
        tipo_codigo=m.tipo_codigo,
        descripcion=m.descripcion,
        nivel=Nivel(m.nivel),
        estado=EstadoEscenario(m.estado),
        es_base=m.es_base,
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
        tareas=[_tarea_a_dominio(t) for t in m.tareas],
    )


def _tarea_a_dominio(t: TareaModel) -> Tarea:
    return Tarea(
        id=t.id,
        enunciado=t.enunciado,
        rol_codigo=t.rol_codigo,
        dificultad=Nivel(t.dificultad),
        criterios=list(t.criterios),
        puntaje_maximo=t.puntaje_maximo,
        tiempo_limite_segundos=t.tiempo_limite_segundos,
        respuesta_esperada=t.respuesta_esperada,
    )


class SqlEscenarioRepository:
    def __init__(self, session: Session):
        self.session = session

    def _consulta(self):
        return select(EscenarioModel).options(
            selectinload(EscenarioModel.roles),
            selectinload(EscenarioModel.injects),
            selectinload(EscenarioModel.tareas),
        )

    def obtener(self, escenario_id: UUID) -> Escenario | None:
        modelo = self.session.scalar(
            self._consulta().where(EscenarioModel.id == escenario_id)
        )
        return _a_dominio(modelo) if modelo else None

    def listar(self, filtro: FiltroEscenarios) -> list[Escenario]:
        q = self._consulta()
        if filtro.texto:
            patron = f"%{filtro.texto}%"
            q = q.where(
                or_(
                    EscenarioModel.nombre.ilike(patron),
                    EscenarioModel.descripcion.ilike(patron),
                )
            )
        if filtro.tipo_codigo:
            q = q.where(EscenarioModel.tipo_codigo == filtro.tipo_codigo)
        if filtro.nivel:
            q = q.where(EscenarioModel.nivel == filtro.nivel.value)
        if filtro.rol_codigo:
            q = q.where(
                EscenarioModel.roles.any(RolEjercicioModel.codigo == filtro.rol_codigo)
            )
        if filtro.estados:
            q = q.where(EscenarioModel.estado.in_([e.value for e in filtro.estados]))
        q = q.order_by(EscenarioModel.nombre)
        return [_a_dominio(m) for m in self.session.scalars(q)]

    def guardar(self, escenario: Escenario) -> Escenario:
        modelo = self.session.get(EscenarioModel, escenario.id)
        if modelo is None:
            modelo = EscenarioModel(id=escenario.id)
            self.session.add(modelo)
        modelo.nombre = escenario.nombre
        modelo.tipo_codigo = escenario.tipo_codigo
        modelo.descripcion = escenario.descripcion
        modelo.nivel = escenario.nivel.value
        modelo.estado = escenario.estado.value
        modelo.es_base = escenario.es_base
        modelo.roles = [
            self.session.get(RolEjercicioModel, codigo) for codigo in escenario.roles
        ]
        # Se reemplazan injects y tareas conservando los id existentes.
        modelo.injects.clear()
        modelo.tareas.clear()
        self.session.flush()
        modelo.injects = [
            InjectModel(
                id=i.id,
                orden=i.orden,
                titulo=i.titulo,
                descripcion=i.descripcion,
                minuto_sugerido=i.minuto_sugerido,
            )
            for i in escenario.injects
        ]
        modelo.tareas = [
            TareaModel(
                id=t.id,
                posicion=pos,
                rol_codigo=t.rol_codigo,
                enunciado=t.enunciado,
                dificultad=t.dificultad.value,
                criterios=t.criterios,
                puntaje_maximo=t.puntaje_maximo,
                tiempo_limite_segundos=t.tiempo_limite_segundos,
                respuesta_esperada=t.respuesta_esperada,
            )
            for pos, t in enumerate(escenario.tareas)
        ]
        self.session.commit()
        return self.obtener(escenario.id)  # type: ignore[return-value]

    def buscar_tareas(self, filtro: FiltroBanco) -> list[TareaDelBanco]:
        q = select(TareaModel, EscenarioModel).join(
            EscenarioModel, TareaModel.escenario_id == EscenarioModel.id
        )
        if filtro.solo_publicados:
            q = q.where(EscenarioModel.estado == EstadoEscenario.PUBLICADO.value)
        else:
            q = q.where(EscenarioModel.estado != EstadoEscenario.ARCHIVADO.value)
        if filtro.tipo_codigo:
            q = q.where(EscenarioModel.tipo_codigo == filtro.tipo_codigo)
        if filtro.rol_codigo:
            q = q.where(TareaModel.rol_codigo == filtro.rol_codigo)
        if filtro.dificultad:
            q = q.where(TareaModel.dificultad == filtro.dificultad.value)
        q = q.order_by(EscenarioModel.nombre, TareaModel.posicion)
        return [
            TareaDelBanco(
                tarea=_tarea_a_dominio(t),
                escenario_id=e.id,
                escenario_nombre=e.nombre,
                tipo_codigo=e.tipo_codigo,
            )
            for t, e in self.session.execute(q)
        ]


class SqlCatalogoRepository:
    def __init__(self, session: Session):
        self.session = session

    def tipos_escenario(self) -> list[TipoEscenario]:
        filas = self.session.scalars(
            select(TipoEscenarioModel).order_by(TipoEscenarioModel.nombre)
        )
        return [
            TipoEscenario(
                codigo=f.codigo,
                nombre=f.nombre,
                descripcion=f.descripcion,
                nivel_complejidad=Nivel(f.nivel_complejidad),
                roles_sugeridos=list(f.roles_sugeridos),
            )
            for f in filas
        ]

    def roles_ejercicio(self) -> list[RolEjercicio]:
        filas = self.session.scalars(
            select(RolEjercicioModel).order_by(RolEjercicioModel.nombre)
        )
        return [RolEjercicio(codigo=f.codigo, nombre=f.nombre) for f in filas]
