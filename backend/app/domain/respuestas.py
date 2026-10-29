"""Respuestas de los participantes a las tareas de su rol (PB-08, RF-02).

Cada participante responde una sola vez cada tarea, dentro de su tiempo
límite. El tiempo corre desde que se lanzó el inject de la tarea y se detiene
mientras la sesión está en pausa.

Núcleo de dominio: no depende de FastAPI ni de SQLAlchemy.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.sesiones import ReglaSesionError, TareaSesion, TipoTarea

# Margen para la latencia de la red: una respuesta enviada en el último segundo
# puede llegar un poco después del límite y se acepta igual.
TOLERANCIA_SEGUNDOS = 2
MAX_TEXTO = 5000


class EstadoTarea(StrEnum):
    PENDIENTE = "pendiente"
    RESPONDIDA = "respondida"
    VENCIDA = "vencida"


@dataclass
class Respuesta:
    sesion_id: UUID
    tarea_id: UUID
    inject_id: UUID
    usuario_id: UUID
    rol_codigo: str
    recibida_en: datetime
    # Segundos efectivos que usó el participante (sin contar pausas).
    segundos_usados: int
    texto: str | None = None
    opciones_elegidas: list[int] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)


def errores_de_contenido(
    tarea: TareaSesion, texto: str | None, opciones: list[int]
) -> list[str]:
    """Qué le falta a la respuesta según el tipo de tarea."""
    if tarea.tipo == TipoTarea.SELECCION_MULTIPLE:
        if texto:
            return ["Esta tarea se responde eligiendo opciones"]
        if not opciones:
            return ["Elige al menos una opción"]
        if len(set(opciones)) != len(opciones):
            return ["Hay opciones repetidas"]
        if any(i < 0 or i >= len(tarea.opciones) for i in opciones):
            return ["Alguna opción elegida no existe"]
        return []
    if opciones:
        return ["Esta tarea se responde con texto"]
    if not texto or not texto.strip():
        return ["Escribe tu respuesta"]
    if len(texto) > MAX_TEXTO:
        return [f"La respuesta no puede superar {MAX_TEXTO} caracteres"]
    return []


def estado_tarea(respuesta: Respuesta | None, segundos_restantes: int) -> EstadoTarea:
    if respuesta is not None:
        return EstadoTarea.RESPONDIDA
    return EstadoTarea.PENDIENTE if segundos_restantes > 0 else EstadoTarea.VENCIDA


def exigir_a_tiempo(tarea: TareaSesion, segundos_usados: int) -> None:
    if segundos_usados > tarea.tiempo_limite_segundos + TOLERANCIA_SEGUNDOS:
        raise ReglaSesionError(["Se agotó el tiempo para esta tarea"])
