"""Esquemas de entrada y salida de la API de escenarios (validación con Pydantic)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    RolEjercicio,
    Tarea,
    TipoEscenario,
)
from app.ports.escenario_repository import TareaDelBanco


class InjectEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID | None = None
    titulo: str = Field(min_length=3, max_length=150)
    descripcion: str = Field(min_length=10, max_length=5000)
    minuto_sugerido: int | None = Field(default=None, ge=0, le=600)


class TareaEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID | None = None
    enunciado: str = Field(min_length=10, max_length=2000)
    rol_codigo: str = Field(min_length=2, max_length=40)
    dificultad: Nivel
    criterios: list[str] = Field(min_length=1, max_length=10)
    puntaje_maximo: int = Field(default=10, ge=1, le=100)
    tiempo_limite_segundos: int = Field(default=300, ge=30, le=3600)
    respuesta_esperada: str | None = Field(default=None, max_length=5000)


class EscenarioEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=150)
    tipo_codigo: str = Field(min_length=2, max_length=40)
    descripcion: str = Field(min_length=20, max_length=5000)
    nivel: Nivel
    roles: list[str] = Field(min_length=1, max_length=15)
    injects: list[InjectEntrada] = Field(default_factory=list, max_length=30)
    tareas: list[TareaEntrada] = Field(default_factory=list, max_length=100)

    def a_dominio(self) -> Escenario:
        """El orden de los injects es su posición en la lista (1, 2, 3...)."""
        return Escenario(
            nombre=self.nombre,
            tipo_codigo=self.tipo_codigo,
            descripcion=self.descripcion,
            nivel=self.nivel,
            roles=self.roles,
            injects=[
                Inject(
                    titulo=i.titulo,
                    descripcion=i.descripcion,
                    orden=pos,
                    minuto_sugerido=i.minuto_sugerido,
                    **({"id": i.id} if i.id else {}),
                )
                for pos, i in enumerate(self.injects, start=1)
            ],
            tareas=[
                Tarea(
                    enunciado=t.enunciado,
                    rol_codigo=t.rol_codigo,
                    dificultad=t.dificultad,
                    criterios=[c.strip() for c in t.criterios if c.strip()],
                    puntaje_maximo=t.puntaje_maximo,
                    tiempo_limite_segundos=t.tiempo_limite_segundos,
                    respuesta_esperada=t.respuesta_esperada,
                    **({"id": t.id} if t.id else {}),
                )
                for t in self.tareas
            ],
        )


class InjectSalida(BaseModel):
    id: UUID
    orden: int
    titulo: str
    descripcion: str
    minuto_sugerido: int | None


class TareaSalida(BaseModel):
    id: UUID
    enunciado: str
    rol_codigo: str
    dificultad: Nivel
    criterios: list[str]
    puntaje_maximo: int
    tiempo_limite_segundos: int
    respuesta_esperada: str | None


class EscenarioResumen(BaseModel):
    id: UUID
    nombre: str
    tipo_codigo: str
    nivel: Nivel
    estado: EstadoEscenario
    roles: list[str]
    total_injects: int
    total_tareas: int

    @classmethod
    def desde(cls, e: Escenario) -> "EscenarioResumen":
        return cls(
            id=e.id,
            nombre=e.nombre,
            tipo_codigo=e.tipo_codigo,
            nivel=e.nivel,
            estado=e.estado,
            roles=e.roles,
            total_injects=len(e.injects),
            total_tareas=len(e.tareas),
        )


class EscenarioDetalle(EscenarioResumen):
    descripcion: str
    es_base: bool
    injects: list[InjectSalida]
    tareas: list[TareaSalida]
    pendientes_para_publicar: list[str]

    @classmethod
    def desde(cls, e: Escenario) -> "EscenarioDetalle":
        return cls(
            **EscenarioResumen.desde(e).model_dump(),
            descripcion=e.descripcion,
            es_base=e.es_base,
            injects=[InjectSalida(**vars(i)) for i in e.injects],
            tareas=[TareaSalida(**vars(t)) for t in e.tareas],
            pendientes_para_publicar=e.errores_para_publicar(),
        )


class TareaBancoSalida(TareaSalida):
    escenario_id: UUID
    escenario_nombre: str
    tipo_codigo: str

    @classmethod
    def desde(cls, item: TareaDelBanco) -> "TareaBancoSalida":
        return cls(
            **vars(item.tarea),
            escenario_id=item.escenario_id,
            escenario_nombre=item.escenario_nombre,
            tipo_codigo=item.tipo_codigo,
        )


class TipoEscenarioSalida(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    nivel_complejidad: Nivel
    roles_sugeridos: list[str]

    @classmethod
    def desde(cls, t: TipoEscenario) -> "TipoEscenarioSalida":
        return cls(**vars(t))


class RolEjercicioSalida(BaseModel):
    codigo: str
    nombre: str

    @classmethod
    def desde(cls, r: RolEjercicio) -> "RolEjercicioSalida":
        return cls(**vars(r))
