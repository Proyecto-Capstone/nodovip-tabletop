"""Catálogo de escenarios profesionales ficticios (PC-46).

Cada escenario sigue las fases de NIST SP 800-61 (detección y análisis,
contención, erradicación y recuperación, actividades posteriores) a lo largo de
4 injects con evidencia simulada (PC-44). Cada pregunta indica en qué inject se
hace y combina texto libre con selección múltiple.
"""

from collections.abc import Callable

from app.catalogo_escenarios.amenaza_interna import escenario_amenaza_interna
from app.catalogo_escenarios.cadena_suministro import escenario_cadena_suministro
from app.catalogo_escenarios.ddos import escenario_ddos
from app.catalogo_escenarios.fuga_datos import escenario_fuga_datos
from app.catalogo_escenarios.phishing import escenario_phishing
from app.catalogo_escenarios.ransomware import escenario_ransomware
from app.domain.escenarios import Escenario

CATALOGO: list[Callable[[], Escenario]] = [
    escenario_ransomware,
    escenario_phishing,
    escenario_fuga_datos,
    escenario_ddos,
    escenario_amenaza_interna,
    escenario_cadena_suministro,
]

__all__ = ["CATALOGO", "escenario_ransomware"]
