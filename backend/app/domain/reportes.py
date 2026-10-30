"""Brechas y recomendaciones del reporte de cierre (PB-14, RF-07).

Una **brecha** es una tarea ya lanzada en la que un participante quedó por
debajo de lo esperado. Se clasifica por tipo y severidad a partir del puntaje
vigente (con los ajustes del moderador) y del detalle del evaluador (PB-10):

| Tipo | Cuándo |
|---|---|
| Sin respuesta | No respondió la tarea (o se le venció el tiempo) |
| Fuera de tiempo | Respondió después del límite |
| Decisión incorrecta | Marcó alguna opción incorrecta |
| Respuesta incompleta | Le faltaron criterios u opciones correctas |

Severidad según el porcentaje obtenido: alta < 40 %, media < 70 %, baja < 85 %.
Desde el 85 % no hay brecha. *Sin respuesta* y *fuera de tiempo* son siempre altas.

Las **recomendaciones** salen de las brechas, una por rol y tipo. Si la misma
brecha (mismo rol y misma tarea) ya apareció en sesiones anteriores del mismo
cliente, es **recurrente** y sube a prioridad alta.

Núcleo de dominio: no depende de FastAPI ni de SQLAlchemy.
"""

import unicodedata
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

UMBRAL_SIN_BRECHA = 0.85
UMBRAL_MEDIA = 0.70
UMBRAL_ALTA = 0.40


class TipoBrecha(StrEnum):
    SIN_RESPUESTA = "sin_respuesta"
    FUERA_DE_TIEMPO = "fuera_de_tiempo"
    DECISION_INCORRECTA = "decision_incorrecta"
    RESPUESTA_INCOMPLETA = "respuesta_incompleta"


ETIQUETA_TIPO = {
    TipoBrecha.SIN_RESPUESTA: "Sin respuesta",
    TipoBrecha.FUERA_DE_TIEMPO: "Fuera de tiempo límite",
    TipoBrecha.DECISION_INCORRECTA: "Decisión incorrecta",
    TipoBrecha.RESPUESTA_INCOMPLETA: "Respuesta incompleta",
}


class Severidad(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


_ORDEN_SEVERIDAD = {Severidad.ALTA: 0, Severidad.MEDIA: 1, Severidad.BAJA: 2}


@dataclass(frozen=True)
class ResultadoTarea:
    """Cómo le fue a un participante en una tarea ya lanzada."""

    usuario_id: UUID
    participante: str
    rol_codigo: str
    rol_nombre: str
    tarea_id: UUID
    tarea: str
    inject_orden: int
    puntaje_maximo: int
    # None si no respondió. Es el vigente: incluye los ajustes del moderador.
    puntaje: float | None
    faltantes: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Brecha:
    participante: str
    rol_codigo: str
    rol_nombre: str
    tarea: str
    inject_orden: int
    tipo: TipoBrecha
    severidad: Severidad
    porcentaje: float
    # Criterios que faltaron u opciones incorrectas marcadas.
    detalle: list[str] = field(default_factory=list)
    # En cuántas sesiones anteriores del mismo cliente apareció.
    recurrente_en: int = 0

    @property
    def clave(self) -> tuple[str, str]:
        """Identifica la brecha entre sesiones: mismo rol y misma tarea."""
        return self.rol_codigo, _normalizar(self.tarea)

    @property
    def etiqueta_tipo(self) -> str:
        return ETIQUETA_TIPO[self.tipo]


@dataclass(frozen=True)
class Recomendacion:
    prioridad: Severidad
    rol_nombre: str
    texto: str
    recurrente: bool = False


def detectar_brechas(resultados: list[ResultadoTarea]) -> list[Brecha]:
    """Brechas de la sesión, de la más severa a la menos y por inject."""
    brechas = [b for r in resultados if (b := _brecha_de(r)) is not None]
    return sorted(
        brechas,
        key=lambda b: (_ORDEN_SEVERIDAD[b.severidad], b.inject_orden, b.rol_nombre),
    )


def marcar_recurrentes(
    brechas: list[Brecha], anteriores: list[list[Brecha]]
) -> list[Brecha]:
    """Cuenta en cuántas sesiones anteriores (del mismo cliente) se repitió."""
    vistas = [{b.clave for b in sesion} for sesion in anteriores]
    return [
        replace(b, recurrente_en=sum(1 for claves in vistas if b.clave in claves))
        for b in brechas
    ]


def superadas(brechas: list[Brecha], anteriores: list[list[Brecha]]) -> list[Brecha]:
    """Brechas de la sesión anterior que ya no aparecen: lo que mejoró."""
    if not anteriores:
        return []
    actuales = {b.clave for b in brechas}
    unicas = {b.clave: b for b in anteriores[0] if b.clave not in actuales}
    return list(unicas.values())


def recomendar(
    brechas: list[Brecha], sesiones_anteriores: int = 0
) -> list[Recomendacion]:
    """Una recomendación por rol y tipo de brecha, las prioritarias primero."""
    if not brechas:
        return [
            Recomendacion(
                Severidad.BAJA,
                "Todos los roles",
                "No se detectaron brechas significativas: mantener el plan de "
                "respuesta actual y repetir el ejercicio con un escenario más exigente.",
            )
        ]
    grupos: dict[tuple[str, TipoBrecha], list[Brecha]] = {}
    for b in brechas:
        grupos.setdefault((b.rol_nombre, b.tipo), []).append(b)
    recomendaciones = []
    for (rol, tipo), del_grupo in grupos.items():
        peor = min(del_grupo, key=lambda b: _ORDEN_SEVERIDAD[b.severidad])
        recurrente = max(b.recurrente_en for b in del_grupo)
        texto = _texto(rol, tipo, del_grupo)
        prioridad = peor.severidad
        if recurrente:
            sesiones = (
                "sesión anterior" if sesiones_anteriores == 1 else "sesiones anteriores"
            )
            texto = (
                f"Brecha recurrente (también en {recurrente} de "
                f"{sesiones_anteriores} {sesiones}). {texto}"
            )
            prioridad = Severidad.ALTA
        recomendaciones.append(Recomendacion(prioridad, rol, texto, bool(recurrente)))
    return sorted(
        recomendaciones,
        key=lambda r: (_ORDEN_SEVERIDAD[r.prioridad], not r.recurrente, r.rol_nombre),
    )


# --- apoyo ----------------------------------------------------------------------------


def _brecha_de(r: ResultadoTarea) -> Brecha | None:
    base = {
        "participante": r.participante,
        "rol_codigo": r.rol_codigo,
        "rol_nombre": r.rol_nombre,
        "tarea": r.tarea,
        "inject_orden": r.inject_orden,
    }
    if r.puntaje is None:
        return Brecha(
            **base,
            tipo=TipoBrecha.SIN_RESPUESTA,
            severidad=Severidad.ALTA,
            porcentaje=0.0,
            detalle=list(r.faltantes),
        )
    proporcion = r.puntaje / r.puntaje_maximo if r.puntaje_maximo else 0.0
    porcentaje = round(100 * proporcion, 1)
    if any("fuera de tiempo" in e.lower() for e in r.errores):
        return Brecha(
            **base,
            tipo=TipoBrecha.FUERA_DE_TIEMPO,
            severidad=Severidad.ALTA,
            porcentaje=porcentaje,
        )
    if proporcion >= UMBRAL_SIN_BRECHA:
        return None
    incorrectas = [e for e in r.errores if "incorrecta" in e.lower()]
    if incorrectas:
        tipo, detalle = TipoBrecha.DECISION_INCORRECTA, incorrectas
    else:
        tipo, detalle = TipoBrecha.RESPUESTA_INCOMPLETA, list(r.faltantes)
    if proporcion < UMBRAL_ALTA:
        severidad = Severidad.ALTA
    elif proporcion < UMBRAL_MEDIA:
        severidad = Severidad.MEDIA
    else:
        severidad = Severidad.BAJA
    return Brecha(
        **base, tipo=tipo, severidad=severidad, porcentaje=porcentaje, detalle=detalle
    )


def _texto(rol: str, tipo: TipoBrecha, brechas: list[Brecha]) -> str:
    tareas = _enumerar(sorted({f"«{b.tarea}»" for b in brechas}))
    if tipo == TipoBrecha.SIN_RESPUESTA:
        return (
            f"Designar un responsable y un suplente para {rol} y practicar la "
            f"respuesta a {tareas}: no hubo respuesta."
        )
    if tipo == TipoBrecha.FUERA_DE_TIEMPO:
        return f"Entrenar a {rol} para decidir dentro del tiempo límite en {tareas}."
    if tipo == TipoBrecha.DECISION_INCORRECTA:
        return (
            f"Revisar con {rol} los criterios de decisión de {tareas}: se marcaron "
            "opciones incorrectas."
        )
    faltantes = sorted({f for b in brechas for f in b.detalle})
    if faltantes:
        return (
            f"Incorporar al procedimiento de {rol}: {'; '.join(faltantes[:4])} "
            f"(faltó en {tareas})."
        )
    return f"Reforzar la preparación de {rol} para {tareas}."


def _enumerar(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return " ".join(
        "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").split()
    )


# --- Contenido del reporte y su PDF guardado --------------------------------------------


@dataclass(frozen=True)
class FilaPuntaje:
    nombre: str
    detalle: str  # rol del participante o número de participantes del rol
    puntaje: float
    maximo: int
    porcentaje: float
    respondidas: int
    sin_responder: int


@dataclass(frozen=True)
class RespuestaReporte:
    """Trazabilidad: cada respuesta con su hora del servidor (PB-09)."""

    recibida_en: datetime
    participante: str
    rol_nombre: str
    inject_orden: int
    tarea: str
    contenido: str
    puntaje: float
    puntaje_maximo: int
    ajustada: bool


@dataclass(frozen=True)
class ReporteSesion:
    sesion_id: UUID
    nombre: str
    cliente: str | None
    escenario: str
    moderador: str
    iniciada_en: datetime | None
    finalizada_en: datetime | None
    participantes: int
    injects_lanzados: int
    total_injects: int
    puntaje_total: float
    maximo_total: int
    por_participante: list[FilaPuntaje]
    por_rol: list[FilaPuntaje]
    brechas: list[Brecha]
    superadas: list[Brecha]
    respuestas: list[RespuestaReporte]
    recomendaciones: list[Recomendacion]
    # Sesiones finalizadas anteriores del mismo cliente usadas como historial.
    sesiones_anteriores: int
    generado_en: datetime

    @property
    def porcentaje_total(self) -> float:
        if not self.maximo_total:
            return 0.0
        return round(100 * self.puntaje_total / self.maximo_total, 1)

    @property
    def duracion_segundos(self) -> int | None:
        if self.iniciada_en is None or self.finalizada_en is None:
            return None
        return int((self.finalizada_en - self.iniciada_en).total_seconds())


class EstadoReporte(StrEnum):
    GENERANDO = "generando"
    GENERADO = "generado"
    FALLIDO = "fallido"


@dataclass
class ReporteGuardado:
    """El último PDF generado de una sesión (uno por sesión)."""

    sesion_id: UUID
    estado: EstadoReporte
    solicitado_en: datetime
    generado_en: datetime | None = None
    pdf: bytes | None = None
    error: str | None = None
