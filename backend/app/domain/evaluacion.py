"""Evaluación automática de respuestas (PB-10, RF-03).

Cada respuesta se califica en tres aspectos entre 0 y 1, ponderados con los
pesos de la sesión (suman 100), sobre el puntaje máximo de la tarea:

    puntaje = puntaje_maximo × (pc·completitud + pp·precisión + pt·tiempo) / 100

- **Selección múltiple:** completitud = correctas elegidas / correctas;
  precisión = correctas elegidas / elegidas. Marcar todo no da puntaje completo.
- **Texto libre:** se buscan las palabras clave de cada criterio en la respuesta
  (sin tildes ni mayúsculas, por raíz de 5 letras para aceptar plurales y
  conjugaciones). Un criterio se cumple si aparece al menos la mitad de sus
  palabras clave. Completitud = criterios cumplidos / criterios; precisión =
  palabras clave encontradas / palabras clave de criterios y respuesta esperada.
  Es una heurística: el moderador puede ajustar el puntaje (AjustePuntaje).
- **Tiempo:** 1 al responder de inmediato y baja hasta 0,5 al llegar al límite:
  responder a tiempo nunca anula este aspecto.
- Sin respuesta o fuera de tiempo (más allá de la tolerancia): 0 puntos.

Núcleo de dominio: no depende de FastAPI ni de SQLAlchemy.
"""

import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.sesiones import (
    PesosPuntuacion,
    ReglaSesionError,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)

# Margen para la latencia de la red al recibir una respuesta (ver respuestas.py).
TOLERANCIA_SEGUNDOS = 2
RAIZ = 5
MIN_MOTIVO = 5

# Palabras que no aportan significado al comparar con los criterios.
VACIAS = frozenset(
    [
        "a",
        "al",
        "algo",
        "algun",
        "alguna",
        "ante",
        "antes",
        "como",
        "con",
        "contra",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "desde",
        "donde",
        "durante",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "era",
        "es",
        "esa",
        "ese",
        "eso",
        "esta",
        "este",
        "esto",
        "estos",
        "estas",
        "fue",
        "ha",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "muy",
        "nada",
        "ni",
        "no",
        "nos",
        "o",
        "otra",
        "otro",
        "para",
        "pero",
        "poco",
        "por",
        "porque",
        "que",
        "quien",
        "se",
        "sea",
        "segun",
        "ser",
        "si",
        "sin",
        "sobre",
        "su",
        "sus",
        "tambien",
        "tan",
        "te",
        "todo",
        "todos",
        "tras",
        "tu",
        "un",
        "una",
        "uno",
        "unos",
        "unas",
        "y",
        "ya",
    ]
)


@dataclass(frozen=True)
class Evaluacion:
    """Resultado del evaluador. Los aspectos van de 0 a 1."""

    puntaje: float
    puntaje_maximo: int
    completitud: float
    precision: float
    tiempo: float
    # Criterios u opciones correctas que cubrió, los que le faltaron y los errores
    # (opciones incorrectas marcadas, fuera de tiempo).
    aciertos: list[str] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def evaluar(
    tarea: TareaSesion,
    pesos: PesosPuntuacion,
    texto: str | None,
    opciones: list[int],
    segundos_usados: int,
) -> Evaluacion:
    if segundos_usados > tarea.tiempo_limite_segundos + TOLERANCIA_SEGUNDOS:
        return _cero(tarea, ["Respuesta fuera de tiempo"])
    if tarea.tipo == TipoTarea.SELECCION_MULTIPLE:
        completitud, precision, aciertos, faltantes, errores = _seleccion(
            tarea, opciones
        )
    else:
        completitud, precision, aciertos, faltantes = _texto(tarea, texto or "")
        errores = []
    if completitud == 0 and precision == 0:
        # Nada correcto: responder rápido no da puntos por sí solo.
        return _cero(tarea, errores, aciertos, faltantes)
    tiempo = _factor_tiempo(segundos_usados, tarea.tiempo_limite_segundos)
    proporcion = (
        pesos.completitud * completitud
        + pesos.precision * precision
        + pesos.tiempo * tiempo
    ) / 100
    return Evaluacion(
        puntaje=round(tarea.puntaje_maximo * proporcion, 2),
        puntaje_maximo=tarea.puntaje_maximo,
        completitud=round(completitud, 3),
        precision=round(precision, 3),
        tiempo=round(tiempo, 3),
        aciertos=aciertos,
        faltantes=faltantes,
        errores=errores,
    )


def sin_respuesta(tarea: TareaSesion) -> Evaluacion:
    """Tarea lanzada que el participante no respondió (o se le venció)."""
    return _cero(tarea, ["Sin respuesta"], faltantes=_esperado(tarea))


# --- Ajuste manual del moderador ------------------------------------------------------


@dataclass
class AjustePuntaje:
    """Cambio manual de puntaje. Se agrega, nunca se modifica: queda el historial."""

    respuesta_id: UUID
    moderador_id: UUID
    puntaje_anterior: float
    puntaje_nuevo: float
    motivo: str
    creado_en: datetime
    id: UUID = field(default_factory=uuid4)


def validar_ajuste(puntaje: float, puntaje_maximo: int, motivo: str) -> None:
    errores = []
    if not math.isfinite(puntaje) or not 0 <= puntaje <= puntaje_maximo:
        errores.append(f"El puntaje debe estar entre 0 y {puntaje_maximo}")
    if len(motivo.strip()) < MIN_MOTIVO:
        errores.append("Explica el motivo del ajuste (al menos 5 caracteres)")
    if errores:
        raise ReglaSesionError(errores)


def puntaje_vigente(evaluacion: Evaluacion, ajustes: list[AjustePuntaje]) -> float:
    """El del último ajuste del moderador o, si no hay, el automático."""
    if not ajustes:
        return evaluacion.puntaje
    return max(ajustes, key=lambda a: a.creado_en).puntaje_nuevo


# --- apoyo ----------------------------------------------------------------------------


def _cero(
    tarea: TareaSesion,
    errores: list[str],
    aciertos: list[str] | None = None,
    faltantes: list[str] | None = None,
) -> Evaluacion:
    return Evaluacion(
        puntaje=0,
        puntaje_maximo=tarea.puntaje_maximo,
        completitud=0,
        precision=0,
        tiempo=0,
        aciertos=aciertos or [],
        faltantes=faltantes if faltantes is not None else _esperado(tarea),
        errores=errores,
    )


def _esperado(tarea: TareaSesion) -> list[str]:
    if tarea.tipo == TipoTarea.SELECCION_MULTIPLE:
        return [o.texto for o in tarea.opciones if o.correcta]
    return list(tarea.criterios)


def _factor_tiempo(usados: int, limite: int) -> float:
    if limite <= 0:
        return 1.0
    return 1 - 0.5 * min(1.0, max(0, usados) / limite)


def _seleccion(tarea: TareaSesion, elegidas: list[int]):
    validas = {i for i in elegidas if 0 <= i < len(tarea.opciones)}
    correctas = {i for i, o in enumerate(tarea.opciones) if o.correcta}
    bien = validas & correctas
    mal = validas - correctas
    completitud = len(bien) / len(correctas) if correctas else 0
    precision = len(bien) / len(validas) if validas else 0
    texto = tarea.opciones
    return (
        completitud,
        precision,
        [texto[i].texto for i in sorted(bien)],
        [texto[i].texto for i in sorted(correctas - bien)],
        [f"Marcó una opción incorrecta: {texto[i].texto}" for i in sorted(mal)],
    )


def _texto(tarea: TareaSesion, respuesta: str):
    # En la respuesta cuentan también las palabras cortas ("TI", "CEO").
    encontradas = _raices(respuesta, cortas=True)
    aciertos, faltantes = [], []
    claves_criterios: set[str] = set()
    for criterio in tarea.criterios:
        claves = _raices(criterio)
        claves_criterios |= claves
        if claves and len(claves & encontradas) / len(claves) >= 0.5:
            aciertos.append(criterio)
        else:
            faltantes.append(criterio)
    todas = claves_criterios | _raices(tarea.respuesta_esperada or "")
    completitud = len(aciertos) / len(tarea.criterios) if tarea.criterios else 0
    precision = len(todas & encontradas) / len(todas) if todas else 0
    return completitud, precision, aciertos, faltantes


def _raices(texto: str, cortas: bool = False) -> set[str]:
    """Raíces de las palabras con significado, sin tildes ni mayúsculas."""
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    palabras = [p for p in re.findall(r"\w+", sin_tildes) if p not in VACIAS]
    largas = [p for p in palabras if len(p) >= 4 or p.isdigit()]
    # Criterios muy cortos ("TI", "CEO"): se comparan las palabras que haya.
    return {p[:RAIZ] for p in (palabras if cortas or not largas else largas)}


# --- Puntaje acumulado por participante y por rol -------------------------------------


@dataclass
class Acumulado:
    puntaje: float = 0
    maximo: int = 0
    respondidas: int = 0
    sin_responder: int = 0

    @property
    def porcentaje(self) -> float:
        return round(100 * self.puntaje / self.maximo, 1) if self.maximo else 0.0

    def sumar(self, puntaje: float | None, maximo: int) -> None:
        self.maximo += maximo
        if puntaje is None:
            self.sin_responder += 1
        else:
            self.respondidas += 1
            self.puntaje = round(self.puntaje + puntaje, 2)


def acumular(
    sesion: SesionTabletop, puntajes: dict[tuple[UUID, UUID], float]
) -> tuple[dict[UUID, Acumulado], dict[str, Acumulado]]:
    """Suma por participante y por rol sobre las tareas de los injects lanzados.

    `puntajes` es el puntaje vigente por (tarea_id, usuario_id). Una tarea ya
    lanzada que no se respondió suma 0 sobre su puntaje máximo.
    """
    orden = {i.id: i.orden for i in sesion.injects}
    por_participante = {p.usuario_id: Acumulado() for p in sesion.participantes}
    por_rol = {r: Acumulado() for r in sesion.roles}
    for p in sesion.participantes:
        for t in sesion.tareas:
            lanzada = orden.get(t.inject_id, math.inf) <= sesion.inject_actual
            if t.rol_codigo != p.rol_codigo or not lanzada:
                continue
            puntaje = puntajes.get((t.id, p.usuario_id))
            por_participante[p.usuario_id].sumar(puntaje, t.puntaje_maximo)
            por_rol.setdefault(p.rol_codigo, Acumulado()).sumar(
                puntaje, t.puntaje_maximo
            )
    return por_participante, por_rol
