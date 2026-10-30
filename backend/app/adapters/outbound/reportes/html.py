"""Plantilla HTML del reporte de brechas (PB-14), según el prototipo P-07 (Figura 22).

Es la presentación del PDF: WeasyPrint la convierte. Se separa de la
conversión para poder probarla sin WeasyPrint. Todo el texto pasa por
`escape`: el reporte incluye respuestas escritas por los participantes.
"""

from datetime import datetime, timedelta, timezone
from html import escape

from app.domain.reportes import (
    Brecha,
    FilaPuntaje,
    Recomendacion,
    ReporteSesion,
    Severidad,
)

# Ecuador continental: UTC-5 todo el año (sin horario de verano).
ZONA_REPORTE = timezone(timedelta(hours=-5), "ECT")

_ETIQUETA_SEVERIDAD = {
    Severidad.ALTA: "Alta",
    Severidad.MEDIA: "Media",
    Severidad.BAJA: "Baja",
}

ESTILOS = """
@page {
  size: A4;
  font-family: "DejaVu Sans", Arial, sans-serif;
  margin: 18mm 15mm 18mm 15mm;
  @bottom-left { content: "NODOVIP Tabletop · Reporte de brechas"; font-size: 8pt; color: #6b7085; }
  @bottom-right { content: "Página " counter(page) " de " counter(pages); font-size: 8pt; color: #6b7085; }
}
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 9.5pt; color: #1c1e2e; }
.barra { background: #1c1d33; color: #fff; padding: 10px 14px; border-radius: 6px; font-weight: bold; }
h1 { font-size: 17pt; margin: 14px 0 2px; }
h2 { font-size: 12pt; margin: 18px 0 6px; padding-bottom: 3px; border-bottom: 2px solid #e1e4ec; page-break-after: avoid; }
.suave { color: #6b7085; }
.meta { margin: 0 0 8px; }
.tarjetas { display: flex; gap: 8px; margin: 8px 0; }
.tarjeta { flex: 1; border: 1px solid #e1e4ec; border-radius: 6px; padding: 8px 10px; }
.tarjeta strong { display: block; font-size: 14pt; }
table { width: 100%; border-collapse: collapse; margin: 4px 0 8px; }
th { text-align: left; background: #eceef3; font-size: 8.5pt; padding: 5px 6px; }
td { padding: 5px 6px; border-top: 1px solid #e1e4ec; vertical-align: top; }
tr { page-break-inside: avoid; }
.barra-puntaje { height: 7px; background: #eceef3; border-radius: 4px; width: 120px; }
.barra-puntaje span { display: block; height: 7px; border-radius: 4px; }
.verde { background: #22874f; } .naranja { background: #c46a0c; } .rojo { background: #c63d3d; }
.sev { padding: 2px 6px; border-radius: 8px; font-size: 8pt; font-weight: bold; }
.sev-alta { background: #fbe7e7; color: #c63d3d; }
.sev-media { background: #fdf0e1; color: #c46a0c; }
.sev-baja { background: #e6eefd; color: #2f6fed; }
.recurrente { color: #c63d3d; font-size: 8pt; font-weight: bold; }
.recomendaciones { background: #f4f1fd; border-left: 4px solid #6b4fd8; padding: 8px 12px; border-radius: 4px; }
.recomendaciones li { margin: 4px 0; }
.vacio { color: #6b7085; font-style: italic; }
"""


def renderizar(r: ReporteSesion) -> str:
    """HTML completo del reporte."""
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Reporte de brechas — {escape(r.nombre)}</title>
<style>{ESTILOS}</style></head>
<body>
<div class="barra">NODOVIP — Reporte de cierre: {escape(r.nombre)}</div>
<h1>Reporte de Brechas Organizacionales</h1>
<p class="meta suave">{_meta(r)}</p>
{_resumen(r)}
{_puntajes(r)}
{_brechas(r)}
{_trazabilidad(r)}
{_recomendaciones(r)}
<p class="suave">Generado el {_fecha(r.generado_en)} (hora de Ecuador, UTC−5).</p>
</body></html>"""


# --- Secciones ------------------------------------------------------------------------


def _meta(r: ReporteSesion) -> str:
    partes = [
        f"Escenario: {escape(r.escenario)}",
        f"Cliente: {escape(r.cliente or 'sin cliente')}",
        f"Fecha: {_fecha(r.iniciada_en)}",
        f"Duración: {_duracion(r.duracion_segundos)}",
        f"Moderador: {escape(r.moderador)}",
        f"Participantes: {r.participantes}",
    ]
    return " · ".join(partes)


def _resumen(r: ReporteSesion) -> str:
    por_sev = {s: sum(1 for b in r.brechas if b.severidad == s) for s in Severidad}
    if r.sesiones_anteriores:
        n = r.sesiones_anteriores
        comparadas = (
            "Se comparó 1 sesión anterior"
            if n == 1
            else f"Se compararon {n} sesiones anteriores"
        )
        historial = (
            f"{comparadas} del cliente: "
            f"{sum(1 for b in r.brechas if b.recurrente_en)} brechas se repiten y "
            f"{len(r.superadas)} ya se superaron."
        )
    elif r.cliente:
        historial = "Es la primera sesión registrada de este cliente."
    else:
        historial = "La sesión no tiene cliente: no hay historial para comparar."
    return f"""<h2>1. Resumen ejecutivo</h2>
<div class="tarjetas">
  <div class="tarjeta"><strong>{r.porcentaje_total} %</strong>
    <span class="suave">Puntaje global ({_num(r.puntaje_total)} / {r.maximo_total})</span></div>
  <div class="tarjeta"><strong>{len(r.brechas)}</strong>
    <span class="suave">Brechas: {por_sev[Severidad.ALTA]} altas, {por_sev[Severidad.MEDIA]} medias,
    {por_sev[Severidad.BAJA]} bajas</span></div>
  <div class="tarjeta"><strong>{r.injects_lanzados}/{r.total_injects}</strong>
    <span class="suave">Injects lanzados</span></div>
  <div class="tarjeta"><strong>{len(r.respuestas)}</strong>
    <span class="suave">Respuestas registradas</span></div>
</div>
<p>{historial}</p>"""


def _puntajes(r: ReporteSesion) -> str:
    return f"""<h2>2. Puntajes finales</h2>
<p><strong>Por rol</strong></p>
{_tabla_puntajes(r.por_rol, "Rol")}
<p><strong>Por participante</strong></p>
{_tabla_puntajes(r.por_participante, "Participante")}"""


def _tabla_puntajes(filas: list[FilaPuntaje], titulo: str) -> str:
    if not filas:
        return '<p class="vacio">Sin datos.</p>'
    cuerpo = "".join(
        f"""<tr><td><strong>{escape(f.nombre)}</strong><br>
<span class="suave">{escape(f.detalle)}</span></td>
<td><div class="barra-puntaje"><span class="{_color(f.porcentaje)}"
 style="width:{min(100, f.porcentaje)}%"></span></div></td>
<td>{_num(f.puntaje)} / {f.maximo} ({f.porcentaje} %)</td>
<td>{f.respondidas} de {f.respondidas + f.sin_responder}</td></tr>"""
        for f in filas
    )
    return f"""<table><thead><tr><th>{titulo}</th><th>Avance</th><th>Puntaje</th>
<th>Respondidas</th></tr></thead><tbody>{cuerpo}</tbody></table>"""


def _brechas(r: ReporteSesion) -> str:
    if not r.brechas:
        cuerpo = '<p class="vacio">No se detectaron brechas en esta sesión.</p>'
    else:
        filas = "".join(_fila_brecha(b) for b in r.brechas)
        cuerpo = f"""<table><thead><tr><th>Rol</th><th>Participante</th><th>Tarea</th>
<th>Tipo de brecha</th><th>Severidad</th><th>Inject</th></tr></thead>
<tbody>{filas}</tbody></table>"""
    superadas = ""
    if r.superadas:
        items = "".join(
            f"<li>{escape(b.rol_nombre)}: «{escape(b.tarea)}»</li>" for b in r.superadas
        )
        superadas = (
            "<p><strong>Superadas respecto a la sesión anterior del cliente</strong></p>"
            f"<ul>{items}</ul>"
        )
    return f"<h2>3. Brechas detectadas por rol</h2>{cuerpo}{superadas}"


def _fila_brecha(b: Brecha) -> str:
    detalle = (
        f'<br><span class="suave">{escape("; ".join(b.detalle[:3]))}</span>'
        if b.detalle
        else ""
    )
    recurrente = (
        f'<br><span class="recurrente">Recurrente ({b.recurrente_en})</span>'
        if b.recurrente_en
        else ""
    )
    return f"""<tr><td><strong>{escape(b.rol_nombre)}</strong></td>
<td>{escape(b.participante)}</td><td>{escape(b.tarea)}{detalle}</td>
<td>{escape(b.etiqueta_tipo)} ({b.porcentaje} %){recurrente}</td>
<td><span class="sev sev-{b.severidad.value}">{_ETIQUETA_SEVERIDAD[b.severidad]}</span></td>
<td>Inject {b.inject_orden}</td></tr>"""


def _trazabilidad(r: ReporteSesion) -> str:
    if not r.respuestas:
        return '<h2>4. Trazabilidad</h2><p class="vacio">No hubo respuestas.</p>'
    filas = "".join(
        f"""<tr><td>{_hora(x.recibida_en)}</td><td>{escape(x.participante)}<br>
<span class="suave">{escape(x.rol_nombre)}</span></td><td>{x.inject_orden}</td>
<td>{escape(x.tarea)}</td><td>{escape(x.contenido)}</td>
<td>{_num(x.puntaje)} / {x.puntaje_maximo}{" (ajustado)" if x.ajustada else ""}</td></tr>"""
        for x in r.respuestas
    )
    return f"""<h2>4. Trazabilidad de respuestas</h2>
<p class="suave">Hora del servidor al recibir cada respuesta. Las respuestas son
inmutables; los ajustes de puntaje quedan registrados.</p>
<table><thead><tr><th>Hora</th><th>Participante</th><th>Inject</th><th>Tarea</th>
<th>Respuesta</th><th>Puntaje</th></tr></thead><tbody>{filas}</tbody></table>"""


def _recomendaciones(r: ReporteSesion) -> str:
    items = "".join(_item_recomendacion(x) for x in r.recomendaciones)
    return f"""<h2>5. Recomendaciones</h2>
<div class="recomendaciones"><ol>{items}</ol></div>"""


def _item_recomendacion(x: Recomendacion) -> str:
    return (
        f'<li><span class="sev sev-{x.prioridad.value}">'
        f"{_ETIQUETA_SEVERIDAD[x.prioridad]}</span> "
        f"<strong>{escape(x.rol_nombre)}:</strong> {escape(x.texto)}</li>"
    )


# --- apoyo ----------------------------------------------------------------------------


def _num(n: float) -> str:
    return f"{n:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _color(porcentaje: float) -> str:
    if porcentaje >= 70:
        return "verde"
    return "naranja" if porcentaje >= 40 else "rojo"


def _fecha(d: datetime | None) -> str:
    return d.astimezone(ZONA_REPORTE).strftime("%d/%m/%Y %H:%M") if d else "—"


def _hora(d: datetime) -> str:
    return d.astimezone(ZONA_REPORTE).strftime("%H:%M:%S")


def _duracion(segundos: int | None) -> str:
    if segundos is None:
        return "—"
    h, resto = divmod(segundos, 3600)
    return f"{h:02d}:{resto // 60:02d}:{resto % 60:02d}"
