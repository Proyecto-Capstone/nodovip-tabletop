"""Atajos para escribir los escenarios del catálogo (PC-46).

Todo el contenido es ficticio: organizaciones, personas, dominios (.test,
.example) y cifras inventadas. Las referencias normativas son reales (NIST SP
800-61, Ley Orgánica de Protección de Datos Personales del Ecuador).
"""

from app.domain.escenarios import (
    Evidencia,
    Inject,
    Nivel,
    NivelAlerta,
    OpcionRespuesta,
    Tarea,
    TipoEvidencia,
    TipoTarea,
)


def inject(
    orden: int, titulo: str, descripcion: str, minuto: int, evidencia: Evidencia
) -> Inject:
    return Inject(
        titulo=titulo,
        descripcion=descripcion,
        orden=orden,
        minuto_sugerido=minuto,
        evidencia=evidencia,
    )


def correo(origen: str, asunto: str, contenido: str) -> Evidencia:
    return Evidencia(TipoEvidencia.CORREO, origen, asunto, contenido)


def alerta(origen: str, asunto: str, contenido: str, nivel: NivelAlerta) -> Evidencia:
    return Evidencia(TipoEvidencia.ALERTA, origen, asunto, contenido, nivel)


def noticia(origen: str, asunto: str, contenido: str) -> Evidencia:
    return Evidencia(TipoEvidencia.NOTICIA, origen, asunto, contenido)


def llamada(origen: str, asunto: str, contenido: str) -> Evidencia:
    return Evidencia(TipoEvidencia.LLAMADA, origen, asunto, contenido)


def mensaje(origen: str, asunto: str, contenido: str) -> Evidencia:
    return Evidencia(TipoEvidencia.MENSAJE, origen, asunto, contenido)


def documento(origen: str, asunto: str, contenido: str) -> Evidencia:
    return Evidencia(TipoEvidencia.DOCUMENTO, origen, asunto, contenido)


def texto(
    rol: str,
    en_inject: int,
    enunciado: str,
    criterios: list[str],
    dificultad: Nivel = Nivel.MEDIO,
    puntaje: int = 10,
    minutos: int = 5,
) -> Tarea:
    """Pregunta abierta: se evalúa con los criterios (palabras clave)."""
    return Tarea(
        enunciado=enunciado,
        rol_codigo=rol,
        dificultad=dificultad,
        criterios=criterios,
        puntaje_maximo=puntaje,
        tiempo_limite_segundos=minutos * 60,
        inject_orden=en_inject,
    )


def seleccion(
    rol: str,
    en_inject: int,
    enunciado: str,
    opciones: list[tuple[str, bool]],
    dificultad: Nivel = Nivel.MEDIO,
    puntaje: int = 10,
    minutos: int = 3,
) -> Tarea:
    """Selección múltiple: `opciones` es (texto, correcta), en el orden a mostrar."""
    return Tarea(
        enunciado=enunciado,
        rol_codigo=rol,
        dificultad=dificultad,
        criterios=[],
        puntaje_maximo=puntaje,
        tiempo_limite_segundos=minutos * 60,
        tipo=TipoTarea.SELECCION_MULTIPLE,
        opciones=[OpcionRespuesta(t, c) for t, c in opciones],
        inject_orden=en_inject,
    )


__all__ = [
    "Nivel",
    "NivelAlerta",
    "alerta",
    "correo",
    "documento",
    "inject",
    "llamada",
    "mensaje",
    "noticia",
    "seleccion",
    "texto",
]
