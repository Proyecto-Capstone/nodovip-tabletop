# Evidencias simuladas y aviso de injects (PC-44)

En un incidente real nadie recibe "el inject 2": recibe un correo sospechoso, una
alerta del SIEM, la llamada de un periodista. Para que el ejercicio sea inmersivo,
cada inject puede llevar una **evidencia simulada** que la sala muestra con el
aspecto de su origen.

## Modelo

`domain/escenarios.py`:

| Elemento | Descripción |
|---|---|
| `TipoEvidencia` | `correo`, `alerta`, `noticia`, `llamada`, `mensaje`, `documento` |
| `NivelAlerta` | `baja`, `media`, `alta`, `critica` (solo para alertas) |
| `Evidencia` | inmutable: `tipo`, `origen`, `asunto`, `contenido`, `nivel` |
| `Inject.evidencia` | `Evidencia \| None`: es opcional |

`Evidencia.a_dict()` / `Evidencia.desde_dict()` convierten a y desde JSON.

Migración `0011`: columna JSON `evidencia` (nullable) en `inject` y en
`sesion_inject`. Los injects existentes quedan sin evidencia. Al crear una sesión
desde un escenario (`SesionTabletop.desde_escenario`) la evidencia se copia con
el inject. El moderador puede cambiarla en el diseñador mientras la sesión es un
borrador.

| Tipo | Origen | Asunto | Se muestra como |
|---|---|---|---|
| correo | Remitente | Asunto | Ventana de bandeja de entrada (De / Asunto / cuerpo) |
| alerta | Sistema que la genera | Título de la alerta | Consola oscura con severidad y detalle en monoespaciado |
| noticia | Medio o red social | Titular | Recorte de prensa con tipografía serif |
| llamada | Quién llama | Motivo | Llamada entrante con transcripción |
| mensaje | Quién escribe | Resumen | Burbuja de chat |
| documento | Emisor | Título | Hoja de documento |

## API

- Escenarios y sesiones: `InjectEntrada` / `InjectSesionEntrada` aceptan
  `evidencia` (opcional) y `InjectSalida` la devuelve. Validación
  (`EvidenciaEsquema`): origen 2–150, asunto 2–200, contenido 5–5000 caracteres;
  un tipo desconocido responde 422. El `nivel` se descarta si el tipo no es
  `alerta`.
- Vista en vivo (`GET .../en-vivo` y WebSocket): `inject` trae su `evidencia`, y
  `lanzados` es la lista de injects ya lanzados, en orden, con
  `lanzado_segundo`: el tiempo efectivo de la sesión (sin pausas) en que se lanzó.
  Es `null` si la sesión se reconstruyó tras perder el estado de Redis.

## Frontend

- `components/Evidencia.tsx`: `EditorEvidencia` (formulario del escenario y paso
  de injects del diseñador) y `EvidenciaSimulada` (presentación por tipo).
  Nombres y etiquetas en `lib/evidencias.ts`.
- La evidencia aparece en el inject actual (sala del participante y panel del
  moderador) y en el detalle del escenario. La lista de injects del panel
  muestra el ícono del tipo.
- `lib/useAvisoInject.ts`: cuando `inject_actual` aumenta,
  - aparece un banner fijo durante 8 s ("Nuevo inject N"), que se puede cerrar;
  - suena una notificación de dos tonos generada con Web Audio, sin archivos.
    El participante puede silenciarla, y la preferencia se guarda en
    `localStorage` (`nodovip_sonido_injects`);
  - si la pestaña está en segundo plano, el título parpadea hasta que vuelva.

  La primera vista que llega (al entrar o reconectar) no avisa. El banner usa
  una región `aria-live` para lectores de pantalla y respeta
  `prefers-reduced-motion`.
- `pages/LineaDeTiempo.tsx`: la "Línea de tiempo del incidente" lista los
  injects anteriores al actual, con el momento en que se lanzó cada uno. Cada
  uno se puede abrir para releer su narrativa y su evidencia.

## Contenido

Las evidencias son siempre ficticias: dominios `.test` o `.example`, medios y
empresas inventadas, sin nombres, cédulas ni correos reales (RNF-02). El seed
`python -m app.seed_escenarios` incluye evidencias en los 4 injects del
escenario de ransomware.

## Pruebas

- Backend: ida y vuelta a JSON, copia a la sesión, API (guardado, nivel solo en
  alertas, tipo inválido 422), vista en vivo con `lanzados` y persistencia
  real en PostgreSQL (`test_repositorio_escenarios_pg.py`).
- Frontend: `components/Evidencia.test.tsx` (editor y los 6 tipos) y
  `pages/EnVivo.test.tsx` (aviso, evidencia, línea de tiempo y silencio).
