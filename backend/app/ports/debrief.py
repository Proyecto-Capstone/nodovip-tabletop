"""Puerto de salida del debrief de una sesión (PC-45)."""

from typing import Protocol
from uuid import UUID

from app.domain.debrief import Debrief


class DebriefRepository(Protocol):
    def obtener(self, sesion_id: UUID) -> Debrief | None: ...

    def guardar(self, debrief: Debrief) -> Debrief:
        """Crea o reemplaza el debrief de la sesión (uno por sesión)."""
        ...
