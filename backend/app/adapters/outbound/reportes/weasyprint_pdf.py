"""Adaptador del puerto GeneradorPdf con WeasyPrint (PB-14).

WeasyPrint necesita Pango del sistema (se instala en la imagen Docker). Se
importa al generar y no al cargar el módulo: así el backend arranca aunque la
librería no esté (por ejemplo, en Windows sin GTK), y solo falla el PDF.
"""

from app.adapters.outbound.reportes.html import renderizar
from app.domain.reportes import ReporteSesion


class GeneradorWeasyPrint:
    def generar(self, reporte: ReporteSesion) -> bytes:
        from weasyprint import HTML  # import diferido a propósito (ver arriba)

        return HTML(string=renderizar(reporte)).write_pdf()
