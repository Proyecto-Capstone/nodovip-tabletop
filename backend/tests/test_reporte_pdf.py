"""PDF real con WeasyPrint (PB-14).

Se salta si WeasyPrint no puede cargar Pango (por ejemplo, en Windows sin GTK).
En Docker y en el CI las librerías están instaladas, así que corre.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.adapters.outbound.reportes import GeneradorWeasyPrint
from app.domain.reportes import (
    FilaPuntaje,
    ReporteSesion,
    ResultadoTarea,
    detectar_brechas,
    recomendar,
)

try:
    import weasyprint  # noqa: F401
except (ImportError, OSError) as e:  # OSError: faltan las librerías de Pango
    pytest.skip(f"WeasyPrint no disponible: {e}", allow_module_level=True)

T0 = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)


def test_genera_un_pdf_valido_con_acentos():
    brechas = detectar_brechas(
        [
            ResultadoTarea(
                usuario_id=uuid4(),
                participante="María Vásquez",
                rol_codigo="legal",
                rol_nombre="Legal",
                tarea_id=uuid4(),
                tarea="¿A quién notifica según la Ley de Protección de Datos?",
                inject_orden=1,
                puntaje_maximo=10,
                puntaje=None,
                faltantes=["Notificar a la autoridad en 72 horas"],
            )
        ]
    )
    reporte = ReporteSesion(
        sesion_id=uuid4(),
        nombre="Simulacro de ransomware",
        cliente="Banco Andino",
        escenario="Ransomware en sucursal",
        moderador="Mónica Moderadora",
        iniciada_en=T0,
        finalizada_en=T0 + timedelta(minutes=45),
        participantes=1,
        injects_lanzados=1,
        total_injects=4,
        puntaje_total=0,
        maximo_total=10,
        por_participante=[FilaPuntaje("María Vásquez", "Legal", 0, 10, 0, 0, 1)],
        por_rol=[FilaPuntaje("Legal", "1 participante", 0, 10, 0, 0, 1)],
        brechas=brechas,
        superadas=[],
        respuestas=[],
        recomendaciones=recomendar(brechas),
        sesiones_anteriores=0,
        generado_en=T0 + timedelta(hours=1),
    )
    pdf = GeneradorWeasyPrint().generar(reporte)
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
