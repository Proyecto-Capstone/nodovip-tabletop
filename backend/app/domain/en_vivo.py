"""Estado en vivo de una sesión tabletop que se está conduciendo (PB-07, RF-02).

Vive en Redis mientras la sesión está en curso. Las fases son los injects:
0 es la apertura (todavía no se lanzó ninguno) y 1..n el inject en pantalla.
El tiempo transcurrido descuenta las pausas.

Núcleo de dominio: no depende de FastAPI, Redis ni SQLAlchemy.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.sesiones import ReglaSesionError


@dataclass
class EstadoEnVivo:
    sesion_id: UUID
    total_injects: int
    iniciada_en: datetime
    inject_actual: int = 0
    inject_lanzado_en: datetime | None = None
    pausada_desde: datetime | None = None
    segundos_en_pausa: float = 0.0
    finalizada_en: datetime | None = None
    # Aumenta con cada cambio: el cliente descarta mensajes viejos.
    version: int = 1

    @property
    def pausada(self) -> bool:
        return self.pausada_desde is not None

    @property
    def cerrada(self) -> bool:
        return self.finalizada_en is not None

    @property
    def quedan_injects(self) -> bool:
        return self.inject_actual < self.total_injects

    def segundos_transcurridos(self, ahora: datetime) -> int:
        fin = self.finalizada_en or ahora
        pausa = self.segundos_en_pausa
        if self.pausada_desde is not None and self.finalizada_en is None:
            pausa += (ahora - self.pausada_desde).total_seconds()
        return max(0, int((fin - self.iniciada_en).total_seconds() - pausa))

    def lanzar_siguiente_inject(self, ahora: datetime) -> None:
        self._exigir_activa()
        if self.pausada:
            raise ReglaSesionError(["Reanuda la sesión antes de lanzar un inject"])
        if not self.quedan_injects:
            raise ReglaSesionError(["Ya se lanzaron todos los injects"])
        self.inject_actual += 1
        self.inject_lanzado_en = ahora
        self.version += 1

    def pausar(self, ahora: datetime) -> None:
        self._exigir_activa()
        if self.pausada:
            raise ReglaSesionError(["La sesión ya está en pausa"])
        self.pausada_desde = ahora
        self.version += 1

    def reanudar(self, ahora: datetime) -> None:
        self._exigir_activa()
        if not self.pausada:
            raise ReglaSesionError(["La sesión no está en pausa"])
        self.segundos_en_pausa += (ahora - self.pausada_desde).total_seconds()
        self.pausada_desde = None
        self.version += 1

    def cerrar(self, ahora: datetime) -> None:
        self._exigir_activa()
        if self.pausada:
            self.reanudar(ahora)
        self.finalizada_en = ahora
        self.version += 1

    def _exigir_activa(self) -> None:
        if self.cerrada:
            raise ReglaSesionError(["La sesión ya terminó"])


@dataclass
class EventoEnVivo:
    """Lo que se difunde a todas las conexiones de una sesión."""

    sesion_id: UUID
    # "estado": cambió el estado en vivo; "presencia": alguien se (des)conectó;
    # "suscrito": la conexión ya escucha (recién ahí se envía la foto inicial,
    # para no perder eventos entre la foto y la suscripción).
    tipo: str
    estado: EstadoEnVivo | None = None
    conectados: frozenset[UUID] = frozenset()
