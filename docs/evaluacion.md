# Evaluación automática y puntaje (PB-10)

Cada respuesta se califica **al recibirla** con el evaluador del dominio
(`backend/app/domain/evaluacion.py`, sin FastAPI ni SQLAlchemy). El resultado se
guarda en la misma fila de `respuesta`, que es inmutable (PB-09): el puntaje
automático original queda como evidencia. El moderador puede ajustarlo, y cada
ajuste se agrega a un historial que tampoco se puede alterar.

## Fórmula (RF-03)

Tres aspectos entre 0 y 1, ponderados con los pesos de la sesión (suman 100,
por defecto 40 / 40 / 20), sobre el puntaje máximo de la tarea:

```
puntaje = puntaje_maximo × (pc·completitud + pp·precisión + pt·tiempo) / 100
```

| Aspecto | Selección múltiple | Texto libre |
|---|---|---|
| Completitud | correctas elegidas / correctas | criterios cumplidos / criterios |
| Precisión | correctas elegidas / elegidas | palabras clave encontradas / palabras clave de los criterios y de la respuesta esperada |
| Tiempo | 1 al responder de inmediato, baja linealmente hasta 0,5 al llegar al límite | igual |

- **Marcar todas las opciones** no da puntaje completo: baja la precisión.
- **Texto libre:** se comparan las palabras con significado (sin tildes,
  mayúsculas ni palabras vacías como "de", "la", "para") por su raíz de 5
  letras, para aceptar plurales y conjugaciones ("notifico" cumple "notificar").
  Un criterio se cumple si aparece al menos la mitad de sus palabras clave. Los
  criterios muy cortos ("TI", "CEO") se comparan con la palabra completa.
- **Nada correcto** (completitud y precisión en 0): 0 puntos. Responder rápido no
  da puntos por sí solo.
- **Sin respuesta** o **fuera de tiempo** (más de 2 s de tolerancia sobre el
  límite): 0 puntos.
- El evaluador también guarda el detalle: criterios u opciones correctas
  cubiertos (`aciertos`), los que faltaron (`faltantes`) y los `errores`
  (opciones incorrectas marcadas, fuera de tiempo).

La evaluación de texto libre es una **heurística de palabras clave**: no entiende
sinónimos ni el sentido de la respuesta. Por eso existe el ajuste manual.
Evaluar con un modelo de lenguaje queda como trabajo futuro.

## Ajuste manual

- Lo hace solo el moderador dueño de la sesión. El puntaje debe estar entre 0 y
  el máximo de la tarea, y el motivo es obligatorio (al menos 5 caracteres).
- Nunca modifica la respuesta. Agrega una fila en `ajuste_puntaje` con el puntaje
  anterior, el nuevo, el motivo, el moderador y la hora.
- **Puntaje vigente:** el del último ajuste o, si no hay, el automático.

## Puntaje acumulado

Por participante y por rol, sobre las tareas de los **injects ya lanzados**
(`sesion.inject_actual`). Una tarea lanzada sin responder suma 0 sobre su
máximo. Incluye puntaje, máximo, porcentaje, respondidas y sin responder. Por
participante se ordena de mayor a menor (el leaderboard, PB-12, lo usará).

## Modelo de datos (migración 0009)

- `respuesta` agrega `puntaje_automatico NUMERIC(6,2)`, `puntaje_maximo`,
  `eval_completitud`, `eval_precision`, `eval_tiempo NUMERIC(4,3)` y
  `eval_detalle JSON` (`{aciertos, faltantes, errores}`). Son NULL en las
  respuestas guardadas antes de 0009; esas se evalúan al consultarlas.
- `ajuste_puntaje`: `id`, `respuesta_id`, `sesion_id`, `moderador_id` (FK
  RESTRICT), `puntaje_anterior`, `puntaje_nuevo` (CHECK ≥ 0), `motivo` (CHECK al
  menos 5 caracteres) y `creado_en`. Índice `(sesion_id, creado_en)`.
- El trigger `tr_ajuste_inmutable` (y `tr_ajuste_sin_truncate`) rechaza UPDATE,
  DELETE y TRUNCATE, con la misma purga controlada de las pruebas que
  `respuesta` (`SET LOCAL nodovip.purgar_respuestas = 'si'`, nunca UPDATE).

## Endpoints

Permiso `sesiones:conducir`, solo el moderador dueño (404 si no lo es).

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/sesiones/{id}/respuestas` | Registro (PB-09) con `puntaje` vigente, `puntaje_automatico`, `puntaje_maximo`, los tres aspectos, `aciertos`, `faltantes`, `errores` y `ajustes` |
| POST | `/api/sesiones/{id}/respuestas/{respuesta_id}/ajustes` | `{ "puntaje": 7.5, "motivo": "…" }` → 201 con la fila actualizada; 404 o 422 |
| GET | `/api/sesiones/{id}/puntajes` | `{participantes: [...], roles: [...]}` con el acumulado |

El participante **no** ve su puntaje (ni la respuesta correcta) mientras responde.

## Frontend

`/sesiones/:id/respuestas` (*Respuestas y puntajes*):

- **Puntaje acumulado** por participante y por rol.
- Cada respuesta muestra el puntaje vigente sobre el máximo. Si se ajustó, lleva
  la marca *Ajustado* con el automático. En *Detalle* se ven los tres aspectos,
  los aciertos, lo que faltó, los errores y el historial de ajustes.
- *Ajustar* abre un formulario con el nuevo puntaje y el motivo. Al guardar se
  recargan el registro y el acumulado.

## Pruebas

- `tests/test_evaluacion.py`: evaluador puro con casos límite:
  - sin respuesta, fuera de tiempo (y dentro de la tolerancia), texto vacío;
  - respuesta parcial, todas las opciones marcadas, solo incorrectas;
  - criterios con tildes, plurales y palabras cortas;
  - efecto de la respuesta esperada y de los pesos, redondeo;
  - validación del ajuste y puntaje vigente.
- `tests/test_api_respuestas.py`:
  - evaluación al recibir, y el participante no ve el puntaje;
  - ajustes con historial, ajuste inválido, permisos;
  - acumulado por participante y rol.
- `tests/test_respuestas_pg.py` (PostgreSQL):
  - el puntaje se guarda con la respuesta;
  - historial de ajustes, y los ajustes no se pueden modificar, borrar ni vaciar.
- `frontend/src/pages/RespuestasSesionPage.test.tsx`: puntaje y detalle,
  acumulado, flujo de ajuste, errores del ajuste e historial.
