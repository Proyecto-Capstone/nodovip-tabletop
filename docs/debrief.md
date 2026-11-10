# Debrief, lecciones aprendidas y resumen del participante (PC-45)

Un ejercicio tabletop no termina al cerrar la sesión. La fase de **lecciones
aprendidas** de NIST SP 800-61 (el *hot wash*) es donde el equipo convierte lo
observado en mejoras concretas. PC-45 la incorpora a la plataforma:

1. El **moderador** registra el debrief: fortalezas, aspectos a mejorar y un
   plan de acción con responsable, plazo y prioridad.
2. Al **completarlo**, las lecciones pasan al **reporte de brechas** (pantalla
   y PDF, sección 6). El PDF se regenera solo.
3. Cada **participante** ve su **resumen personal**: su puntaje, su posición y
   la retroalimentación de cada tarea. Las lecciones aparecen cuando el
   debrief se completa.

## Dominio (`domain/debrief.py`)

| Elemento | Reglas |
|---|---|
| `Debrief` | Uno por sesión. Estado `borrador` o `completado`. |
| `editar()` | Solo en borrador. Quita espacios y elementos vacíos. Máximo 20 elementos por lista, 1000 caracteres cada uno. |
| `AccionMejora` | Descripción de 5 a 500 caracteres, prioridad `alta` / `media` / `baja`, rol responsable (uno de los roles de la sesión, o ninguno = "Toda la organización") y plazo. |
| `completar()` | Exige al menos 1 fortaleza, 1 mejora y 1 acción, y que toda acción tenga un plazo que no esté en el pasado. Devuelve la lista de lo que falta. |
| `reabrir()` | Vuelve a borrador para corregirlo. |

Migración `0012`: tabla `debrief` (PK = `sesion_id`, FK RESTRICT a `sesion` y
`usuario`). Las fortalezas, las mejoras y las acciones se guardan en JSON, junto
con el estado y las fechas de creación, actualización y completado.

## API (`adapters/inbound/api/debrief.py`)

Solo para sesiones **finalizadas**. Antes de eso, o si la sesión es de otro
moderador, responde 404.

| Método y ruta | Permiso | Descripción |
|---|---|---|
| `GET /api/sesiones/{id}/debrief` | `reportes:ver` (el moderador, solo sus sesiones) | Devuelve el debrief. Si no existe: `estado: "sin_iniciar"` y listas vacías. Incluye `puede_editar` y los roles de la sesión. |
| `PUT /api/sesiones/{id}/debrief` | `sesiones:conducir`, solo el dueño | Guarda el borrador (422 con `errores` si el formato es inválido o el debrief está completado). |
| `POST .../debrief/completar` | ídem | Lo completa (422 con lo que falta) y regenera el PDF en segundo plano (`get_tarea_reporte`). |
| `POST .../debrief/reabrir` | ídem | Lo devuelve a borrador. |
| `GET /api/mis-sesiones/{id}/resumen` | `sesiones:participar`, solo los invitados | Resumen personal. |

Analista y Administrador ven el debrief en solo lectura (`puede_editar: false`).
El participante no accede al debrief: solo ve las lecciones ya completadas,
dentro de su resumen.

### Resumen del participante

`ServicioResumenParticipante` reutiliza el registro de respuestas (PB-09) y el
puntaje vigente (PB-10). Para cada tarea de su rol cuyo inject se lanzó, el
resumen incluye:

- su respuesta (o "no respondió") y el puntaje vigente;
- `aciertos`, `faltantes` y `errores` de la evaluación (sin respuesta: los
  criterios esperados);
- las opciones correctas de la selección múltiple, que se muestran porque la
  sesión ya terminó;
- el motivo del último ajuste del moderador.

También trae su posición entre los participantes.

## Reporte

`ReporteSesion.lecciones` solo existe si el debrief está **completado**.
`ServicioReportes` recibe el repositorio de debriefs como parámetro opcional.
La pantalla y el PDF agregan la sección **6. Lecciones aprendidas y plan de
acción**: fortalezas, mejoras y tabla del plan, con el texto escapado. Si no
está completado, la sección lo indica.

## Frontend

- `/sesiones/:id/debrief` (`DebriefPage.tsx`):
  - Listas editables de fortalezas y mejoras.
  - Editor del plan de acción con responsable, prioridad y plazo.
  - Barra inferior fija con "Guardar borrador" y "Completar debrief", más un
    indicador de cambios sin guardar.
  - Panel lateral **Hallazgos del ejercicio** con las recomendaciones del
    reporte y un botón "+ Agregar al plan", que crea la acción con su
    responsable y prioridad.
  - Si está completado, se ve en solo lectura con el botón "Reabrir para
    editar".
- Accesos al debrief: el panel del moderador al finalizar ("Hacer el
  debrief"), "Mis tabletops" (acción "Debrief") y la sección 6 del reporte.
- `components/Lecciones.tsx`: presentación compartida por el reporte, el
  debrief y el resumen.
- Sala del participante (`ResumenParticipante.tsx`): al finalizar la sesión,
  muestra el resultado (porcentaje, puntos y posición), cada tarea con la
  retroalimentación por colores y las lecciones del ejercicio. En el detalle de
  la sesión aparece el botón "Ver mi resultado y retroalimentación".

## Pruebas

- `tests/test_debrief_dominio.py`: limpieza, validaciones, requisitos para
  completar, reabrir y JSON.
- `tests/test_api_debrief.py`:
  - el ciclo completo y los permisos por rol;
  - el 404 para un moderador ajeno o una sesión sin finalizar;
  - las lecciones en el reporte solo al completar;
  - el resumen con aciertos, opciones correctas y ajuste, la exclusión de
    injects no lanzados y el acceso solo de invitados.
- `tests/test_reportes.py`: sección 6 del HTML, escapada.
  `tests/test_repositorio_sesiones_pg.py`: persistencia en PostgreSQL.
- Frontend: `DebriefPage.test.tsx` (guardar, agregar desde una recomendación,
  errores al completar, solo lectura y analista) y `EnVivo.test.tsx` (resumen
  al finalizar).
