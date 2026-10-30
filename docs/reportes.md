# Reporte PDF de puntajes y brechas (PB-14)

Al cerrar una sesión se genera, en segundo plano, un **reporte de cierre**: datos
de la sesión, puntajes por participante y por rol, brechas detectadas y
clasificadas, respuestas con su hora y recomendaciones de mejora. Las
recomendaciones consideran las **sesiones anteriores del mismo cliente**.

## Arquitectura (hexagonal)

| Capa | Archivo | Qué hace |
|---|---|---|
| Dominio | `app/domain/reportes.py` | Detecta y clasifica brechas, marca recurrentes y superadas, redacta recomendaciones. Sin FastAPI ni SQLAlchemy |
| Aplicación | `app/application/reportes.py` | `ServicioReportes`: arma el contenido (registro PB-09 + puntaje PB-10), busca el historial del cliente, genera y guarda el PDF |
| Puertos | `app/ports/reportes.py` | `GeneradorPdf` y `ReporteRepository` |
| Adaptador PDF | `app/adapters/outbound/reportes/` | `html.py` (plantilla, según el prototipo P-07) y `weasyprint_pdf.py` (WeasyPrint) |
| Persistencia | `models_reportes.py`, `repositorio_reportes.py` | Tabla `reporte`: el último PDF de cada sesión |
| API | `app/adapters/inbound/api/reportes.py` | Endpoints y la tarea de fondo del cierre |

## Brechas

Una brecha es una tarea **ya lanzada** en la que un participante quedó por debajo
de lo esperado. Se usa el **puntaje vigente**: si el moderador ajustó el puntaje
(PB-10), el ajuste cuenta.

| Tipo | Cuándo | Severidad |
|---|---|---|
| Sin respuesta | No respondió (o se le venció el tiempo) | Alta |
| Fuera de tiempo límite | Respondió después del límite | Alta |
| Decisión incorrecta | Marcó opciones incorrectas | Según el % |
| Respuesta incompleta | Le faltaron criterios u opciones correctas | Según el % |

Severidad según el porcentaje obtenido: **alta** < 40 %, **media** < 70 %,
**baja** < 85 %. Desde el 85 % no hay brecha.

## Historial del cliente y recomendaciones

- La sesión tiene un campo opcional **Cliente / organización** (migración 0010).
  Se edita en el paso "Programar" del diseñador. Se normaliza: espacios de más
  fuera, y la comparación no distingue mayúsculas.
- Se comparan las **5 sesiones finalizadas más recientes** del mismo cliente,
  anteriores a esta:
  - **Recurrente:** la misma brecha (mismo rol y misma tarea, sin importar tildes
    ni mayúsculas) ya apareció antes. Su recomendación sube a prioridad alta y
    va primero.
  - **Superada:** estaba en la sesión anterior y ahora ya no.
- Sin cliente no hay historial (se indica en el reporte).
- **Recomendaciones:** una por rol y tipo de brecha, con plantillas según el tipo
  (designar responsable y suplente, entrenar tiempos, revisar criterios de
  decisión o incorporar al procedimiento los criterios que faltaron). Sin brechas,
  se recomienda mantener el plan y subir la exigencia del escenario.

## Generación del PDF

- **Al cerrar la sesión**, `POST /api/sesiones/{id}/en-vivo/cerrar` responde de
  inmediato y agrega una tarea de fondo (`BackgroundTasks`) que abre su propia
  sesión de BD y genera el PDF. El motor en vivo no espera a WeasyPrint (medido:
  el cierre responde en ~24 ms y el PDF queda listo en segundos).
- La tarea **nunca lanza**: si falla, el reporte queda en estado `fallido` con el
  error y se puede regenerar.
- `GET .../pdf` devuelve el PDF guardado; si no existe o falló, lo genera en ese
  momento.
- **WeasyPrint** necesita Pango del sistema: se instala en la imagen Docker
  (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz-subset0`,
  `fonts-dejavu-core`) y en el CI. En Windows sin GTK no carga: el backend
  arranca igual (la importación es diferida) y la prueba del PDF real se salta.
- Las horas del PDF van en hora de Ecuador (UTC−5). Todo el texto se escapa:
  incluye respuestas escritas por los participantes.

## Modelo de datos (migración 0010)

- `sesion.cliente VARCHAR(120) NULL`, con índice.
- `reporte`: `sesion_id` (PK, FK RESTRICT), `estado` (`generando`, `generado` o
  `fallido`), `solicitado_en`, `generado_en`, `pdf BYTEA` y `error`. Guarda solo el
  último PDF: regenerar lo reemplaza (no es evidencia, se puede rehacer con los
  datos inmutables).

## Endpoints

Permiso `reportes:ver` (Analista, Moderador y Administrador). El **Moderador**
solo ve sus sesiones; **Analista** y **Administrador**, cualquier sesión
finalizada. Una sesión que no está finalizada (o ajena para el moderador)
responde 404.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/reportes` | Sesiones finalizadas visibles con el estado de su PDF |
| GET | `/api/reportes/{id}` | Contenido del reporte (pantalla) y estado del PDF |
| GET | `/api/reportes/{id}/pdf` | Descarga (`application/pdf`, adjunto) |
| POST | `/api/reportes/{id}/regenerar` | Vuelve a generar el PDF; 503 si WeasyPrint falla |

## Frontend

- **Reportes** (`/reportes`, menú): sesiones finalizadas con cliente, fecha y
  estado del PDF.
- **Reporte de brechas** (`/reportes/:id`), según el prototipo P-07 (Figura 22):
  - índice lateral con las 5 secciones;
  - resumen ejecutivo con métricas e historial del cliente;
  - puntajes finales por rol (barras verde, naranja o roja) y por participante;
  - brechas por rol con severidad y marca de recurrente;
  - trazabilidad y recomendaciones;
  - botones *Exportar PDF* y *Regenerar PDF*.
- Accesos: *Reporte* en Mis tabletops y *Ver reporte* en el panel del moderador
  cuando la sesión terminó.
- Usuaria demo: `analista@demo.nodovip.test` (`python -m app.seed_usuarios_demo`).

## Pruebas

- `tests/test_reportes_dominio.py`:
  - tipos y severidades, umbral del 85 %;
  - un ajuste que cierra la brecha;
  - recurrentes y superadas, recomendaciones con prioridad.
- `tests/test_reportes.py`:
  - contenido completo, tarea sin responder, efecto de los ajustes;
  - historial del mismo cliente (y no de otro), sin cliente;
  - acceso, PDF generado una vez y reutilizado, fallo registrado;
  - HTML escapado.
- `tests/test_api_reportes.py`:
  - permisos por rol (analista, moderador, administrador; participante y
    observador 403), moderador ajeno y sesión sin finalizar 404;
  - descarga, regenerar, 503 si falla;
  - el cierre programa el reporte en segundo plano.
- `tests/test_reporte_pdf.py`: PDF real con WeasyPrint (se salta sin Pango).
- `tests/test_repositorio_sesiones_pg.py`: cliente y tabla `reporte` en PostgreSQL.
- `frontend/src/pages/ReportePage.test.tsx`: pantalla del reporte, exportar,
  regenerar, error 503, 404 y lista.
