"""Puertos de salida de la biblioteca de escenarios (M2)."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Nivel,
    RolEjercicio,
    Tarea,
    TipoEscenario,
)


@dataclass
class FiltroEscenarios:
    texto: str | None = None
    tipo_codigo: str | None = None
    nivel: Nivel | None = None
    rol_codigo: str | None = None
    estados: list[EstadoEscenario] | None = None


@dataclass
class FiltroBanco:
    tipo_codigo: str | None = None
    rol_codigo: str | None = None
    dificultad: Nivel | None = None
    solo_publicados: bool = True


@dataclass
class TareaDelBanco:
    tarea: Tarea
    escenario_id: UUID
    escenario_nombre: str
    tipo_codigo: str


class EscenarioRepository(Protocol):
    def obtener(self, escenario_id: UUID) -> Escenario | None: ...

    def listar(self, filtro: FiltroEscenarios) -> list[Escenario]: ...

    def guardar(self, escenario: Escenario) -> Escenario: ...

    def buscar_tareas(self, filtro: FiltroBanco) -> list[TareaDelBanco]: ...


class CatalogoRepository(Protocol):
    def tipos_escenario(self) -> list[TipoEscenario]: ...

    def roles_ejercicio(self) -> list[RolEjercicio]: ...
