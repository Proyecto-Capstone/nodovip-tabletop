# Tareas por rol y respuestas del participante (PB-08)

Módulo M3, requisito RF-02. Durante la sesión en vivo (`docs/en-vivo.md`), cada
participante ve las tareas de **su rol** a medida que el moderador lanza los
injects, con el tiempo restante y un campo para responder. Pantalla según el
prototipo P-04 (vista del participante, Figura 19).

## Reglas

- **Enrutamiento por rol:** el participante solo ve las tareas de su rol cuyo
  inject ya se lanzó. Las de otro rol o de un inject futuro responden **404**
  (no se revela que existen).
- **Sin la respuesta correcta:** la API envía solo el texto de las opciones; nunca
  cuál es la correcta, ni los criterios de evaluación, ni la respuesta esperada.
- **Tiempo:** cada tarea tiene su `tiempo_limite_segundos`, que corre desde que
  se lanzó su inject y **se detiene en las pausas**. Se acepta una tolerancia de
  2 s por la latencia de la red; después, **422** "Se agotó el tiempo".
- **Una sola vez:** cada participante responde una vez cada tarea. Un segundo
  envío responde **409**. La respuesta no se puede modificar.
- **En pausa** no se aceptan respuestas (**422**).
- **Contenido:** texto libre requiere texto (hasta 5000 caracteres); selección
  múltiple requiere al menos una opción válida y sin repetir (puede elegir
  varias: "marca todas las que correspondan").

## Cómo se mide el tiempo

El estado en vivo guarda, para cada inject, los segundos efectivos de la sesión
en que se lanzó (`EstadoEnVivo.lanzamientos`). El tiempo usado en una tarea es
`segundos_transcurridos(ahora) − lanzamientos[inject]`; como
`segundos_transcurridos` descuenta las pausas, el tiempo de las tareas también.

Si Redis pierde el estado y se reconstruye desde PostgreSQL, no queda registro
de los lanzamientos: las tareas vuelven a tener su tiempo completo desde ese
momento (a favor del participante).

## Modelo de datos (migración 0007)

Tabla `respuesta`:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | |
| `sesion_id` | uuid FK → `sesion` | RESTRICT, indexada con `usuario_id` |
| `tarea_id` | uuid FK → `sesion_tarea` | RESTRICT |
| `inject_id` | uuid FK → `sesion_inject` | RESTRICT |
| `usuario_id` | uuid FK → `usuario` | RESTRICT |
| `rol_codigo` | varchar(40) FK → `rol_ejercicio` | rol con el que respondió |
| `texto` | text NULL | texto libre |
| `opciones_elegidas` | json | índices elegidos (selección múltiple) |
| `recibida_en` | timestamptz | hora del **servidor** |
| `segundos_usados` | integer | tiempo efectivo, CHECK ≥ 0 |

`UNIQUE (tarea_id, usuario_id)`: la base es la última barrera contra respuestas
dobles (por ejemplo, dos pestañas enviando a la vez). Las FK RESTRICT impiden
borrar una sesión, tarea o usuario con respuestas registradas.

**Contenido fijo durante la ejecución.** Antes, guardar una sesión reescribía
sus tareas e injects. Ahora solo se reescriben mientras la sesión es editable
(borrador o programada); en curso o finalizada se actualizan los datos de
ejecución y el estado de las invitaciones, y las tareas a las que apuntan las
respuestas no cambian.

## Endpoints

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/api/mis-sesiones/{id}/tareas` | Tareas lanzadas de su rol: enunciado, tipo, opciones (texto), tiempo restante, estado (`pendiente`, `respondida`, `vencida`) y su respuesta si ya respondió |
| POST | `/api/mis-sesiones/{id}/tareas/{tarea_id}/respuesta` | `{ "texto": "…" }` o `{ "opciones": [0, 2] }` → 201 con la tarea respondida; 404, 409 o 422 según las reglas |

Ambos requieren el permiso `sesiones:participar`.

## Frontend

`TareasDelRol` (`src/pages/TareasDelRol.tsx`), dentro de la sala del
participante:

- Tarjeta "Tu tarea — {rol}" con el inject, la pregunta y la cuenta regresiva
  (en rojo los últimos 30 s; se detiene en pausa).
- Texto libre o casillas de opciones; el botón *Enviar respuesta* se habilita
  cuando hay contenido.
- Tras enviar: "✓ Respuesta enviada. Ya no se puede modificar." y la respuesta
  en solo lectura. Al vencer el tiempo: "Se agotó el tiempo para esta tarea."
- Cada cambio de la sesión (inject nuevo, pausa) vuelve a pedir las tareas; se
  muestran las últimas conocidas mientras tanto, para no perder lo que se está
  escribiendo.

## Pruebas

- `tests/test_respuestas.py`: enrutamiento por rol, tiempo con pausas,
  tolerancia, una sola respuesta, validación del contenido, reconstrucción.
- `tests/test_api_respuestas.py`: la API no expone la respuesta correcta; 201,
  409, 404 y 422; permisos.
- `tests/test_repositorio_sesiones_pg.py`: en PostgreSQL, guardar una sesión en
  curso no recrea las tareas y la restricción UNIQUE rechaza la segunda
  respuesta.
- `frontend/src/pages/TareasDelRol.test.tsx`: envío de texto y de opciones,
  vencida, pausa, conflicto 409 y sala sin tareas.
