# Leaderboard en vivo para observadores (PB-12, RF-02)

Ranking por participante y por rol de una sesión en curso o finalizada,
actualizado en tiempo real (≤ 3 s). El Observador solo tiene lectura: no ve
respuestas individuales ni puede interactuar con la sesión.

## Reglas de acceso

Permiso `leaderboard:ver` (401 sin sesión, 403 sin el permiso: lo tienen
Observador, Administrador y Moderador).

| Rol | Qué ve |
|---|---|
| Observador, Administrador | Cualquier sesión en curso o finalizada |
| Moderador | Solo las suyas (la de otro moderador responde 404, igual que si no existiera) |
| Participante, Analista | 403 (no tienen `leaderboard:ver`) |

Una sesión en **borrador** o **programada** responde 404 para cualquiera: todavía
no hay nada que mostrar. "Es moderador" se decide por el permiso
`sesiones:conducir`, con el mismo criterio que `ws_sesion` (PB-07): no por el
nombre del rol, para no tener que tocar este código si algún día otro rol
recibe ese permiso.

## Qué datos NO se muestran, y por qué

El leaderboard **nunca** incluye el texto de una respuesta, las opciones
elegidas, los criterios de evaluación, la respuesta esperada ni la opción
correcta. Solo lleva, por participante y por rol: posición, nombre, rol,
puntaje, máximo, porcentaje, respondidas y sin responder.

Esto no es un filtro que se pueda olvidar: `ServicioLeaderboard` reutiliza
`ServicioRegistroRespuestas.acumulado_de` (el mismo cálculo de PB-10), que
devuelve `Acumulado` (puntaje, máximo, respondidas, sin responder) — una
estructura que **no tiene** un campo de texto, opciones ni criterios. Las
dataclasses propias del leaderboard (`SesionLeaderboard`, `PosicionParticipante`,
`PosicionRol`, `RankingLeaderboard`) tampoco los referencian. No hay nada que
filtrar porque nunca se carga: un observador ve el progreso y el resultado,
no el contenido de lo que respondió cada quien (eso es solo para el moderador
dueño, en `/sesiones/{id}/respuestas`, PB-09).

## Ranking y empates

Por participante, de mayor a menor **porcentaje** (no puntos absolutos); por
rol, igual. Las tareas tienen distinto puntaje máximo (10, 15...), así que
ordenar por puntos haría que un 15/15 ganara a un 10/10 aunque ambos
respondieran perfecto; con el porcentaje como criterio principal eso ya no
pasa. Los puntos absolutos solo desempatan cuando el porcentaje coincide
exactamente (`_clave_ranking` en `app/application/leaderboard.py`). Los
empates comparten posición y la siguiente salta (ranking de competencia
estándar: 1, 1, 3, no 1, 2, 2). Un ajuste de puntaje (PB-10) recalcula el
ranking al momento, porque usa el puntaje vigente (el del último ajuste, o el
automático si no hay ninguno).

Con 0 puntos no hay mérito que premiar: el podio y la medalla (ver
"Frontend") solo aplican con posición ≤ 3 **y** puntaje > 0. Un empate en 0
en el puesto 2 o 3, por ejemplo, queda solo en el ranking completo, con su
número de posición y sin fondo destacado.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/leaderboard/sesiones` | Sesiones visibles: `id`, `nombre`, `estado`, `inject_actual`/`total_injects`, `iniciada_en`, `finalizada_en` |
| GET | `/api/leaderboard/sesiones/{id}` | `{ sesion, actualizado_en, participantes: [...], roles: [...] }` |

## WebSocket

`ws(s)://<host>/api/ws/leaderboard/{sesion_id}`, autenticado con la cookie de
sesión. Es de **solo recepción**: el cliente no puede enviar comandos.

1. Al suscribirse, envía `{"tipo": "leaderboard", "datos": {...}}` con el
   ranking completo.
2. Lo vuelve a enviar cada vez que llega un evento `respuesta`, `ajuste` o
   `estado` de la sesión (el mismo canal de PB-07/PB-11). Ignora `presencia`
   (quién está conectado no afecta al ranking) y cualquier tipo futuro que no
   reconozca.
3. **Agrupa las ráfagas:** como máximo un recálculo por segundo por conexión.
   Si llegan varias respuestas casi juntas, se calcula una sola vez, con el
   estado más reciente en ese momento — nunca una vez por cada evento. Sigue
   cumpliendo el requisito de ≤ 3 s: el límite solo puede *agregar* hasta 1 s
   de espera dentro de una ráfaga, nunca más.
4. No retiene una conexión de PostgreSQL entre envíos: abre y cierra su propia
   sesión de base en cada cálculo (`calculador_ranking`, igual que
   `obtener_usuario_ws`), porque el WebSocket puede durar horas.

| Código de cierre | Significado |
|---|---|
| 1000 | La sesión terminó (se envía antes el ranking final) |
| 4401 | Sin sesión iniciada |
| 4403 | El rol no tiene `leaderboard:ver` |
| 4404 | Sesión no visible (no existe, no está en curso/finalizada, o es de otro moderador) |
| otro | Corte de red: el cliente reconecta con espera creciente (0,5 s a 5 s) |

## Modelo de datos

Ninguno nuevo: PB-12 es de solo lectura sobre lo que ya existe (`sesion`,
`respuesta`, `ajuste_puntaje`). No hace falta una migración.

## Frontend

- `/leaderboard`: sesiones en curso o finalizadas visibles para el usuario.
- `/leaderboard/:id`: tablero oscuro según el prototipo P-06 (Figura 21),
  dentro de la cabecera habitual (nombre, inject actual, estado):
  - **Ranking por rol organizacional**: una fila por rol con una barra de
    color según su porcentaje (verde ≥ 70 %, naranja ≥ 40 %, rojo por debajo);
    sin números ni medallas, en el orden ya calculado por el backend.
  - **Podio**: hasta 3 bloques (2º-1º-3º, el 1º más alto y destacado) con
    quienes tienen posición ≤ 3 y puntaje > 0. Con menos de 3 participantes
    así, se muestran menos bloques; con ninguno, no se muestra el podio.
  - **Ranking completo**: columna con todos los participantes numerados por
    posición, con scroll propio; las filas del podio llevan un fondo sutil.
  Indicador "● EN VIVO" y "Actualizado hace X s" mientras está conectado; al
  finalizar la sesión muestra "Resultado final" y deja de reconectar.
  `useLeaderboard` sigue la misma estrategia de reconexión que `useEnVivo`
  (espera creciente, cierre en `pagehide`, reconexión en `pageshow`, sin
  reintentos ante 4401/4403/4404/1000).
- Opción **Leaderboard** en el menú solo con el permiso `leaderboard:ver`, y un
  enlace **Ver leaderboard** desde el panel del moderador y desde el registro
  de respuestas, mientras la sesión está en curso o finalizada.

## Pruebas

- `tests/test_leaderboard.py`: `ServicioLeaderboard` con dobles — Observador y
  Administrador ven cualquier sesión en curso o finalizada; el Moderador solo
  las suyas (otra → 404); borrador o programada → 404 para cualquiera; sin
  sesión → 404; empates comparten posición; un ajuste cambia el ranking; el
  ranking ordena por porcentaje y no por puntos absolutos (un 8/10 le gana a
  un 9/20).
- `tests/test_api_leaderboard.py`: matriz de permisos (401/403/404) por los dos
  endpoints REST; el JSON no contiene texto de tareas, opciones ni criterios;
  WebSocket — ranking al conectar, de nuevo tras una respuesta y tras un
  ajuste, cierre 1000 al finalizar, 4403 al participante, y que diez avisos
  seguidos producen un solo recálculo sin pasar de 3 s.
- `frontend/src/pages/LeaderboardPage.test.tsx` y
  `LeaderboardSesionPage.test.tsx`: lista con datos/vacía/con error, ranking
  con datos, sin participantes, cierre definitivo del WebSocket, actualización
  al llegar un mensaje nuevo sin recargar, "Resultado final", y que un empate
  en 0 puntos no entra al podio ni se destaca en el ranking completo.
- `frontend/src/components/Layout.test.tsx`: la opción del menú solo aparece
  con `leaderboard:ver`.

### Latencia medida

Contra la aplicación real (NGINX, Redis, PostgreSQL), desde que el
participante envía la respuesta hasta que el observador recibe el ranking
actualizado por WebSocket, sin recargar:

- **32 a 60 ms** para un evento aislado (fuera de la ventana de la ráfaga).
- **≈ 1,0 s** cuando el evento llega dentro del segundo siguiente al envío
  anterior: lo absorbe el límite de "como máximo un recálculo por segundo"
  (punto 3 de la sección WebSocket), que es intencional.

En ambos casos, muy por debajo del requisito de ≤ 3 s.
