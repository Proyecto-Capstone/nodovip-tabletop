"""Entidades y reglas de negocio de escenarios (M2, RF-04).

Núcleo de dominio: no depende de FastAPI, SQLAlchemy ni de ningún framework.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

MIN_INJECTS_PARA_PUBLICAR = 3


class Nivel(StrEnum):
    """Nivel de complejidad de un escenario o de dificultad de una tarea."""

    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class EstadoEscenario(StrEnum):
    BORRADOR = "borrador"
    PUBLICADO = "publicado"
    ARCHIVADO = "archivado"


class ReglaEscenarioError(ValueError):
    """Un escenario no cumple una regla de negocio de RF-04."""

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("; ".join(errores))


@dataclass
class TipoEscenario:
    codigo: str
    nombre: str
    descripcion: str
    nivel_complejidad: Nivel
    roles_sugeridos: list[str] = field(default_factory=list)


@dataclass
class RolEjercicio:
    """Rol organizacional que asume un participante (CISO, Legal, TI...)."""

    codigo: str
    nombre: str


@dataclass
class Inject:
    titulo: str
    descripcion: str
    orden: int
    minuto_sugerido: int | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class Tarea:
    """Pregunta o tarea del banco, dirigida a un rol y con criterios de evaluación."""

    enunciado: str
    rol_codigo: str
    dificultad: Nivel
    criterios: list[str]
    puntaje_maximo: int = 10
    tiempo_limite_segundos: int = 300
    respuesta_esperada: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class Escenario:
    nombre: str
    tipo_codigo: str
    descripcion: str
    nivel: Nivel
    roles: list[str]
    injects: list[Inject] = field(default_factory=list)
    tareas: list[Tarea] = field(default_factory=list)
    estado: EstadoEscenario = EstadoEscenario.BORRADOR
    es_base: bool = True
    id: UUID = field(default_factory=uuid4)

    def errores_para_publicar(self) -> list[str]:
        """Devuelve las reglas de RF-04 que el escenario todavía no cumple."""
        errores: list[str] = []
        if len(self.injects) < MIN_INJECTS_PARA_PUBLICAR:
            errores.append(
                f"Debe tener al menos {MIN_INJECTS_PARA_PUBLICAR} injects "
                f"(tiene {len(self.injects)})"
            )
        if not self.roles:
            errores.append("Debe tener al menos un rol involucrado")
        roles_con_tareas = {t.rol_codigo for t in self.tareas}
        sin_tareas = [r for r in self.roles if r not in roles_con_tareas]
        if sin_tareas:
            errores.append("Faltan tareas para los roles: " + ", ".join(sin_tareas))
        return errores

    def validar_consistencia(self) -> None:
        """Reglas que se cumplen siempre, incluso en borrador."""
        errores: list[str] = []
        if len(set(self.roles)) != len(self.roles):
            errores.append("Hay roles repetidos")
        roles = set(self.roles)
        ajenas = sorted({t.rol_codigo for t in self.tareas} - roles)
        if ajenas:
            errores.append(
                "Hay tareas para roles que no están en el escenario: "
                + ", ".join(ajenas)
            )
        ordenes = [i.orden for i in self.injects]
        if len(set(ordenes)) != len(ordenes):
            errores.append("Hay injects con el mismo orden")
        if errores:
            raise ReglaEscenarioError(errores)

    def publicar(self) -> None:
        if self.estado == EstadoEscenario.ARCHIVADO:
            raise ReglaEscenarioError(["No se puede publicar un escenario archivado"])
        self.validar_consistencia()
        errores = self.errores_para_publicar()
        if errores:
            raise ReglaEscenarioError(errores)
        self.estado = EstadoEscenario.PUBLICADO

    def archivar(self) -> None:
        self.estado = EstadoEscenario.ARCHIVADO

    def reemplazar_contenido(self, nuevo: "Escenario") -> None:
        """Actualiza el contenido. Si ya está publicado, debe seguir siendo publicable."""
        if self.estado == EstadoEscenario.ARCHIVADO:
            raise ReglaEscenarioError(["No se puede editar un escenario archivado"])
        nuevo.validar_consistencia()
        if self.estado == EstadoEscenario.PUBLICADO:
            errores = nuevo.errores_para_publicar()
            if errores:
                raise ReglaEscenarioError(errores)
        self.nombre = nuevo.nombre
        self.tipo_codigo = nuevo.tipo_codigo
        self.descripcion = nuevo.descripcion
        self.nivel = nuevo.nivel
        self.roles = nuevo.roles
        self.injects = nuevo.injects
        self.tareas = nuevo.tareas
