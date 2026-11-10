"""Debrief (hot wash) y lecciones aprendidas de una sesión finalizada (PC-45).

Al terminar el ejercicio, el moderador registra lo que funcionó (fortalezas), lo
que hay que mejorar y un plan de acción con responsable, plazo y prioridad. Es
la fase de "lecciones aprendidas" de NIST SP 800-61.

- Se guarda como **borrador** y se edita libremente.
- Al **completarlo** queda fijo y pasa al reporte de brechas (PB-14). Se puede
  reabrir para corregirlo; al completarlo de nuevo se regenera el reporte.

Núcleo de dominio: no depende de FastAPI ni de SQLAlchemy.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

MAX_ELEMENTOS = 20
MAX_TEXTO = 1000
MIN_ACCION = 5
MAX_ACCION = 500


class EstadoDebrief(StrEnum):
    BORRADOR = "borrador"
    COMPLETADO = "completado"


class PrioridadAccion(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class ReglaDebriefError(ValueError):
    """El debrief no cumple una regla de negocio."""

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("; ".join(errores))


@dataclass(frozen=True)
class AccionMejora:
    """Una acción del plan. Sin rol responsable, la asume toda la organización."""

    descripcion: str
    prioridad: PrioridadAccion = PrioridadAccion.MEDIA
    rol_codigo: str | None = None
    plazo: date | None = None

    def a_dict(self) -> dict:
        return {
            "descripcion": self.descripcion,
            "prioridad": self.prioridad.value,
            "rol_codigo": self.rol_codigo,
            "plazo": self.plazo.isoformat() if self.plazo else None,
        }

    @classmethod
    def desde_dict(cls, d: dict) -> "AccionMejora":
        return cls(
            descripcion=d["descripcion"],
            prioridad=PrioridadAccion(d.get("prioridad") or "media"),
            rol_codigo=d.get("rol_codigo"),
            plazo=date.fromisoformat(d["plazo"]) if d.get("plazo") else None,
        )


def _limpiar(textos: list[str]) -> list[str]:
    """Quita espacios y elementos vacíos, conservando el orden."""
    return [t.strip() for t in textos if t and t.strip()]


def _errores_lista(nombre: str, textos: list[str]) -> list[str]:
    errores = []
    if len(textos) > MAX_ELEMENTOS:
        errores.append(f"{nombre}: máximo {MAX_ELEMENTOS} elementos")
    if any(len(t) > MAX_TEXTO for t in textos):
        errores.append(f"{nombre}: cada elemento admite hasta {MAX_TEXTO} caracteres")
    return errores


@dataclass
class Debrief:
    sesion_id: UUID
    autor_id: UUID
    creado_en: datetime
    actualizado_en: datetime
    fortalezas: list[str] = field(default_factory=list)
    mejoras: list[str] = field(default_factory=list)
    acciones: list[AccionMejora] = field(default_factory=list)
    estado: EstadoDebrief = EstadoDebrief.BORRADOR
    completado_en: datetime | None = None

    @property
    def completado(self) -> bool:
        return self.estado == EstadoDebrief.COMPLETADO

    def editar(
        self,
        fortalezas: list[str],
        mejoras: list[str],
        acciones: list[AccionMejora],
        roles_validos: set[str],
        ahora: datetime,
    ) -> None:
        """Reemplaza el contenido del borrador. Valida formato, no completitud."""
        if self.completado:
            raise ReglaDebriefError(
                ["El debrief está completado: reábrelo para editarlo"]
            )
        fortalezas = _limpiar(fortalezas)
        mejoras = _limpiar(mejoras)
        acciones = [
            replace(a, descripcion=a.descripcion.strip())
            for a in acciones
            if a.descripcion and a.descripcion.strip()
        ]
        errores = _errores_lista("Fortalezas", fortalezas)
        errores += _errores_lista("Aspectos a mejorar", mejoras)
        if len(acciones) > MAX_ELEMENTOS:
            errores.append(f"Plan de acción: máximo {MAX_ELEMENTOS} acciones")
        for n, a in enumerate(acciones, start=1):
            if not MIN_ACCION <= len(a.descripcion) <= MAX_ACCION:
                errores.append(
                    f"Acción {n}: la descripción debe tener entre {MIN_ACCION} y "
                    f"{MAX_ACCION} caracteres"
                )
            if a.rol_codigo is not None and a.rol_codigo not in roles_validos:
                errores.append(f"Acción {n}: el rol responsable no es de esta sesión")
        if errores:
            raise ReglaDebriefError(errores)
        self.fortalezas = fortalezas
        self.mejoras = mejoras
        self.acciones = acciones
        self.actualizado_en = ahora

    def pendientes_para_completar(self, hoy: date) -> list[str]:
        """Lo que falta para cerrar el debrief (vacío = se puede completar)."""
        pendientes = []
        if not self.fortalezas:
            pendientes.append("Registra al menos una fortaleza")
        if not self.mejoras:
            pendientes.append("Registra al menos un aspecto a mejorar")
        if not self.acciones:
            pendientes.append("Agrega al menos una acción al plan")
        for n, a in enumerate(self.acciones, start=1):
            if a.plazo is None:
                pendientes.append(f"Acción {n}: indica un plazo")
            elif a.plazo < hoy:
                pendientes.append(f"Acción {n}: el plazo no puede estar en el pasado")
        return pendientes

    def completar(self, ahora: datetime) -> None:
        if self.completado:
            raise ReglaDebriefError(["El debrief ya está completado"])
        pendientes = self.pendientes_para_completar(ahora.date())
        if pendientes:
            raise ReglaDebriefError(pendientes)
        self.estado = EstadoDebrief.COMPLETADO
        self.completado_en = ahora
        self.actualizado_en = ahora

    def reabrir(self, ahora: datetime) -> None:
        if not self.completado:
            raise ReglaDebriefError(["El debrief ya está en borrador"])
        self.estado = EstadoDebrief.BORRADOR
        self.completado_en = None
        self.actualizado_en = ahora
