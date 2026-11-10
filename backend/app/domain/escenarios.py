"""Entidades y reglas de negocio de escenarios (M2, RF-04).

Núcleo de dominio: no depende de FastAPI, SQLAlchemy ni de ningún framework.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

MIN_INJECTS_PARA_PUBLICAR = 3
MIN_OPCIONES = 2


class Nivel(StrEnum):
    """Nivel de complejidad de un escenario o de dificultad de una tarea."""

    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class TipoTarea(StrEnum):
    TEXTO_LIBRE = "texto_libre"
    SELECCION_MULTIPLE = "seleccion_multiple"


@dataclass(frozen=True)
class OpcionRespuesta:
    texto: str
    correcta: bool = False


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


class TipoEvidencia(StrEnum):
    """Forma en que el inject llega a los participantes, como en un incidente real."""

    CORREO = "correo"
    ALERTA = "alerta"
    NOTICIA = "noticia"
    LLAMADA = "llamada"
    MENSAJE = "mensaje"
    DOCUMENTO = "documento"


class NivelAlerta(StrEnum):
    """Severidad con que una consola (SIEM, EDR) muestra una alerta."""

    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


@dataclass(frozen=True)
class Evidencia:
    """Artefacto simulado que acompaña a un inject (PC-44): un correo, una
    alerta, una noticia… Siempre ficticio. El nivel solo aplica a alertas."""

    tipo: TipoEvidencia
    origen: str
    asunto: str
    contenido: str
    nivel: NivelAlerta | None = None

    def a_dict(self) -> dict:
        return {
            "tipo": self.tipo.value,
            "origen": self.origen,
            "asunto": self.asunto,
            "contenido": self.contenido,
            "nivel": self.nivel.value if self.nivel else None,
        }

    @classmethod
    def desde_dict(cls, datos: dict | None) -> "Evidencia | None":
        if not datos:
            return None
        nivel = datos.get("nivel")
        return cls(
            tipo=TipoEvidencia(datos["tipo"]),
            origen=datos["origen"],
            asunto=datos["asunto"],
            contenido=datos["contenido"],
            nivel=NivelAlerta(nivel) if nivel else None,
        )


@dataclass
class Inject:
    titulo: str
    descripcion: str
    orden: int
    minuto_sugerido: int | None = None
    evidencia: Evidencia | None = None
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
    # PC-46: el banco también guarda preguntas de selección múltiple.
    tipo: TipoTarea = TipoTarea.TEXTO_LIBRE
    opciones: list[OpcionRespuesta] = field(default_factory=list)
    # Inject en el que se pregunta (su orden). None: se reparte en orden.
    inject_orden: int | None = None
    id: UUID = field(default_factory=uuid4)

    def errores_de_contenido(self) -> list[str]:
        """Texto libre se evalúa con criterios; selección múltiple, con las
        opciones correctas. Lo comparten el escenario y la sesión."""
        return errores_de_tarea(
            self.enunciado, self.tipo, self.opciones, self.criterios
        )


def errores_de_tarea(
    enunciado: str,
    tipo: TipoTarea,
    opciones: list[OpcionRespuesta],
    criterios: list[str],
) -> list[str]:
    inicio = enunciado[:40]
    if tipo == TipoTarea.SELECCION_MULTIPLE:
        errores = []
        if len(opciones) < MIN_OPCIONES:
            errores.append(
                f'La tarea "{inicio}" necesita al menos {MIN_OPCIONES} opciones'
            )
        if not any(o.correcta for o in opciones):
            errores.append(f'La tarea "{inicio}" no tiene una opción correcta')
        return errores
    if not criterios:
        return [f'La tarea "{inicio}" necesita al menos un criterio de evaluación']
    return []


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
        for t in self.tareas:
            errores += t.errores_de_contenido()
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
        if any(
            t.inject_orden is not None and t.inject_orden not in ordenes
            for t in self.tareas
        ):
            errores.append("Hay tareas asignadas a un inject que no existe")
        if any(t.tipo == TipoTarea.TEXTO_LIBRE and t.opciones for t in self.tareas):
            errores.append("Las tareas de texto libre no llevan opciones")
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
