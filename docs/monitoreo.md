# Monitoreo de hasta 10 sesiones simultáneas (PC-24, PB-13)

El Administrador ve, desde un solo panel, todas las sesiones `EN_CURSO` a la
vez (hasta el límite configurado) y puede entrar a cualquiera en un modo de
**solo lectura**, sin interferir con el moderador que la conduce. Reutiliza el
mismo cálculo de avance que el panel del moderador (PB-11) y el leaderboard
(PB-12, `docs/leaderboard.md`).

## Reglas de acceso

Permiso `sesiones:monitorear` (401 sin sesión, 403 sin el permiso). Hoy solo
lo tiene el Administrador, pero el código no depende del nombre del rol, igual
que `leaderboard:ver` y `sesiones:conducir`: cualquier otro rol que algún día
reciba ese permiso queda cubierto sin tocar nada.

| Endpoint | Qué devuelve |
|---|---|
| `GET /api/monitoreo/sesiones` | Cupo (`activas`/`maximo`) y una fila por cada sesión `EN_CURSO` |
| `GET /api/monitoreo/sesiones/{id}` | Detalle de una sola; 404 si no existe o ya no está en curso |
| `ws /api/ws/monitoreo/{id}` | El mismo detalle, en tiempo real |

## Qué datos NO se muestran, y por qué

Igual que el leaderboard: **nunca** se incluye el texto de una respuesta, las
opciones elegidas ni los criterios de evaluación. `ServicioMonitoreo`
(`app/application/monitoreo.py`) reutiliza
`ServicioRegistroRespuestas.acumulado_de` (el mismo cálculo de PB-10), que
devuelve `Acumulado` — una estructura sin esos campos. En el frontend,
`MonitoreoSesionPage` solo reutiliza `ProgresoParticipantes` y `AvancePorRol`
de `PanelAvance.tsx` (los mismos componentes del panel del moderador): nunca
monta `RespuestasRecientes`, así que el texto nunca llega siquiera a
descargarse para esa vista.

El modo lectura tampoco ofrece **ningún comando ni ajuste de puntaje**: eso
sigue exigiendo `sesiones:conducir` y ser el dueño de la sesión, y la página
no llama a esos endpoints ni renderiza esos botones.

## El administrador no cuenta como "conectado"

El WebSocket de monitoreo (`ws_monitoreo` en
`app/adapters/inbound/api/monitoreo.py`) calcula y envía el mismo detalle que
ve el moderador, pero **a propósito nunca llama a `ServicioEnVivo.conectar`**.
Así, el Administrador que entra en modo lectura no aparece en la lista de
`conectados` ni en el contador que ven los participantes ni el moderador —
mirar no es participar. Lo cubre
`tests/test_api_monitoreo.py::test_websocket_envia_el_detalle_y_no_registra_al_administrador_como_conectado`,
que conecta por WebSocket al administrador y verifica que
`GET /api/sesiones/{id}/en-vivo` (`total_conectados`) y
`GET /api/monitoreo/sesiones` (`conectados`) no cambian.

## Límite configurable de sesiones activas

`MAX_SESIONES_ACTIVAS_POR_DEFECTO = 10` vive en `app/domain/sesiones.py` como
única fuente: `config.max_sesiones_activas()` la usa de valor por defecto (la
variable de entorno `MAX_SESIONES_ACTIVAS` la sobrescribe, debe ser un entero
≥ 1 o `verificar_configuracion()` falla al arrancar) y `ServicioEnVivo` recibe
ese máximo como `maximo_activas` desde la inyección de dependencias
(`get_servicio_en_vivo`, `app/adapters/inbound/api/en_vivo.py`).

Al intentar iniciar una sesión número 11 (o la que corresponda al límite
configurado), `ServicioEnVivo.iniciar` responde 422 con:

> "Se alcanzó el máximo de 10 sesiones activas. Espera a que termine una o
> pide al administrador que amplíe el límite."

y, si alguna de las sesiones activas ya lleva más tiempo corrido que su
duración programada, agrega una frase (singular o plural según cuántas):

> "... 2 de las sesiones activas ya superan su duración programada."

El panel del moderador (`ConducirSesionPage.tsx`) no necesitó ningún cambio
para mostrar este mensaje: su manejo de errores ya mostraba tal cual cualquier
`ApiError.errores` devuelto por un 422 (el mismo camino que usan todas las
reglas de PB-07). Lo confirma
`frontend/src/pages/EnVivo.test.tsx::'si el servidor rechaza por el límite de
sesiones activas, muestra el mensaje tal cual'`.

### Por qué el candado depende de READ COMMITTED

`SqlSesionRepository.iniciar_si_hay_cupo` toma un advisory lock de
PostgreSQL (`pg_advisory_xact_lock`, clave `924_100_024`) y, **dentro** de ese
lock, cuenta las sesiones `EN_CURSO` y guarda la nueva en la misma transacción
— así dos arranques simultáneos nunca pueden superar `maximo_activas`. Esto
depende de que la sesión de SQLAlchemy esté en el nivel de aislamiento por
defecto de PostgreSQL, **READ COMMITTED** (`database.py` no fija
`isolation_level`): el conteo debe ver las filas que confirmaron las *otras*
transacciones mientras esta esperaba el lock, no la foto de antes de pedirlo.

Con **REPEATABLE READ** el conteo vería el mismo snapshot que ya tenía la
transacción al leer la sesión más arriba (en `ServicioEnVivo.iniciar`), aunque
otra transacción hubiera confirmado su "en_curso" mientras tanto — y el
límite se podría superar. Si alguna vez se sube el nivel de aislamiento, el
conteo tendría que hacerse en su propia subtransacción que fuerce ver el
estado ya confirmado tras el lock. El comentario completo está en el
docstring de `iniciar_si_hay_cupo`.

`tests/test_limite_sesiones_pg.py` ejercita justo esta dependencia contra
PostgreSQL real: lanza 12 arranques a la vez (cada uno con su propia conexión,
como 12 requests distintos) contra un límite de 10, y verifica que exactamente
10 tienen éxito y 2 son rechazados con el mensaje del límite — nunca más de
10 filas `EN_CURSO` en la base al final. Se corrió 5 veces seguidas sin
fallos.

## Sesiones que podrían estar abandonadas

`excede_duracion(sesion, ahora)` (en `app/application/en_vivo.py`) compara el
tiempo de **reloj real** transcurrido desde `iniciada_en` contra
`duracion_minutos` (no el `segundos_transcurridos` de `EstadoEnVivo`, que
descuenta las pausas: lo que importa aquí es cuánto tiempo lleva ocupando un
cupo, con o sin pausas). `ServicioMonitoreo` lo expone como
`FilaMonitoreo.excede_duracion`, y tanto el panel (`MonitoreoPage.tsx`, badge
naranja "Excede la duración: X de Y min") como el mensaje del límite (arriba)
lo usan para avisar al Administrador.

**Riesgo conocido, fuera de alcance de esta historia:** PC-24 solo *detecta y
muestra* esta situación; no hay ninguna acción automática ni manual para
cerrar una sesión abandonada desde el panel de monitoreo. Si un moderador
nunca cierra su sesión, sigue ocupando un cupo indefinidamente. Una futura
historia podría agregar que el Administrador la cierre a la fuerza desde este
panel, dejando un registro con el motivo (quién la cerró y por qué), para no
perder trazabilidad de una decisión que no tomó el moderador dueño.

## Aislamiento entre sesiones simultáneas (RNF-04)

Cada sesión usa sus propias claves de Redis (`docs/en-vivo.md`), lo que ya
aislaba el estado en vivo. `tests/test_aislamiento_en_vivo.py` lo verifica
explícitamente con 10 sesiones a la vez (el máximo por defecto), contra el
adaptador en memoria siempre y contra Redis real cuando existe
`TEST_REDIS_URL` (base 1, para no tocar el estado de la aplicación en la base
0):

- guardar en paralelo desde 10 hilos nunca mezcla el estado entre sesiones;
- la lista de conectados es independiente por sesión;
- eliminar una sesión no afecta a las demás;
- ningún suscriptor de WebSocket recibe eventos de otra sesión.

## Modelo de datos

Ninguno nuevo: PC-24 es de solo lectura sobre lo que ya existe (`sesion`,
`respuesta`, `ajuste_puntaje`, el estado en vivo de Redis). No hace falta una
migración.

## Frontend

- **`/monitoreo`**: tarjeta de cupo ("N de M sesiones activas", barra que se
  pone roja al llegar al máximo) y una tarjeta por sesión activa (moderador,
  escenario, métricas, badge de "excede la duración" si corresponde, enlace
  **Ver en modo lectura**). Se refresca cada 5 s (`useResumenMonitoreo`),
  pausado mientras la pestaña no está visible.
- **`/monitoreo/:id`**: banner fijo "Modo lectura — no puedes controlar esta
  sesión.", cabecera con el estado en vivo y un enlace al leaderboard, las
  mismas métricas que el panel del moderador, y **Progreso por participante**
  / **Avance por rol** (de `PanelAvance.tsx`) en modo lectura — sin
  "Respuestas recientes" ni ningún botón de comando. `useDetalleMonitoreo`
  sigue la misma estrategia de reconexión que `useLeaderboard` (espera
  creciente, cierre en `pagehide`/reconexión en `pageshow`, sin reintentos
  ante un cierre definitivo).
- Opción **Monitoreo** en el menú solo con el permiso `sesiones:monitorear`.

| Código de cierre del WebSocket | Significado |
|---|---|
| 4401 | Sin sesión iniciada |
| 4403 | El rol no tiene `sesiones:monitorear` |
| 4404 | La sesión no existe o ya no está en curso |
| otro | Corte de red: el cliente reconecta con espera creciente (0,5 s a 5 s) |

## Datos de prueba: `seed_sesiones_demo`

```
docker compose exec backend python -m app.seed_sesiones_demo [cantidad]
```

Crea `cantidad` sesiones `PROGRAMADA` (10 por defecto, el mismo valor que
`MAX_SESIONES_ACTIVAS_POR_DEFECTO`) del escenario demo, con la moderadora demo
y los cinco participantes demo repartidos uno por rol — listas para
arrancarse a mano y así ver el panel de monitoreo con varias sesiones
`en_curso` a la vez. Requiere que ya hayan corrido `seed_usuarios_demo` y
`seed_escenarios`; es idempotente (omite los nombres que ya existen) y se
niega a correr si `APP_ENV=production`.

## Pruebas

- `tests/test_config.py`: `max_sesiones_activas()` por defecto (10),
  configurable por `MAX_SESIONES_ACTIVAS`, y que un valor inválido
  (`0`, negativo, no numérico) hace fallar `verificar_configuracion()`.
- `tests/test_limite_sesiones.py`: la sesión 11 se rechaza con el límite por
  defecto; un límite distinto se respeta; cerrar una sesión libera un cupo; el
  mensaje de límite menciona cuántas sesiones activas exceden su duración;
  `excede_duracion` es falso sin `iniciada_en`/sin duración programada y
  compara correctamente contra la duración programada.
- `tests/test_limite_sesiones_pg.py`: 12 arranques a la vez contra
  PostgreSQL real nunca superan el máximo de 10 (ver más arriba).
- `tests/test_monitoreo.py`: el resumen solo incluye sesiones `EN_CURSO` y
  trae cupo/máximo; cada fila trae moderador, escenario, invitados,
  conectados y avance; el detalle responde 404 si la sesión no está en curso
  o no existe; el detalle trae avance por participante y rol sin texto de
  respuestas, con `conectados_ids`; una sesión que excede su duración queda
  marcada.
- `tests/test_api_monitoreo.py`: matriz de permisos (401/403); una sesión
  programada no aparece hasta que se inicia; detalle de una sesión en curso;
  404 si no está en curso o no existe; el WebSocket rechaza sin sesión, sin
  permiso o si no está en curso; el WebSocket envía el detalle y **no**
  registra al administrador como conectado.
- `tests/test_aislamiento_en_vivo.py`: aislamiento del estado en vivo entre
  10 sesiones simultáneas (ver RNF-04 más arriba), en memoria y contra Redis
  real.
- `frontend/src/pages/MonitoreoPage.test.tsx`: permiso, cupo, sesiones
  activas con enlace a modo lectura, lista vacía, cupo lleno, badge de
  duración excedida, error del servidor.
- `frontend/src/pages/MonitoreoSesionPage.test.tsx`: permiso, avance por
  participante y rol sin comandos ni texto de respuestas, `conectados_ids`
  marca correctamente a cada participante, cierre definitivo del WebSocket.
- `frontend/src/pages/EnVivo.test.tsx`: el panel del moderador muestra tal
  cual el mensaje 422 del límite de sesiones activas.
- `frontend/src/components/Layout.test.tsx`: la opción del menú solo aparece
  con `sesiones:monitorear`.

### Prueba manual con 10 sesiones

Contra la aplicación real (NGINX, Redis, PostgreSQL), con
`seed_sesiones_demo` y las 10 sesiones iniciadas a mano: el panel de
monitoreo las mostró todas, el intento de una 11ª sesión devolvió el mensaje
de límite, y el modo lectura reflejó el avance de un participante respondiendo
sin recargar la página. Detalle y tiempos en la descripción del PR.
