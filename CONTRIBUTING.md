# Estándares de desarrollo — Proyecto Capstone NODOVIP

Acuerdos del equipo (José Pérez y Romel Gualoto) para trabajar en este repositorio.

## Ramas

| Rama | Uso |
|---|---|
| `main` | Versiones estables. Se despliega a Demo. |
| `develop` | Integración diaria. Se despliega a Staging. |
| `feature/PC-<n>-descripcion-corta` | Una rama por ticket de Jira, creada desde `develop`. |
| `fix/PC-<n>-descripcion-corta` | Corrección de un defecto registrado como Bug en Jira. |

Ejemplo: `feature/PC-13-gestion-usuarios`.

## Commits

- Formato: `PC-<n> verbo en presente + qué cambia`.
- Ejemplos: `PC-13 agrega endpoint para crear usuarios`, `PC-14 corrige validación de injects`.
- Un commit = un cambio con sentido. Nada de `cambios`, `fix` o `wip` sueltos.
- La clave `PC-<n>` va siempre al inicio: así GitHub vincula el commit con Jira.

## Pull requests

1. Título: `PC-<n> descripción`. Base: `develop`.
2. Completar la plantilla del PR.
3. **El pipeline de CI debe estar en verde.**
4. **El otro integrante revisa y aprueba** antes del merge. Nadie aprueba ni mergea su propio PR.
5. Después del merge, borrar la rama y mover el ticket en Jira.

> El plan gratuito de GitHub no permite proteger ramas en repositorios privados, así que los puntos 3 y 4 se cumplen por acuerdo del equipo.

Nadie hace `push` directo a `main` ni a `develop`.

## Definition of Done

Una historia está terminada solo si:

- [ ] Está implementada en frontend y backend, cuando corresponda.
- [ ] Tiene validaciones básicas de entrada.
- [ ] Tiene pruebas unitarias o de integración.
- [ ] Tiene documentación técnica (docstrings, README o `docs/`).
- [ ] Pasa el pipeline de CI.
- [ ] Está desplegada en el ambiente de pruebas (Staging).

## Código

- **Arquitectura hexagonal:** la lógica de negocio va en `backend/app/domain/` y no importa FastAPI ni SQLAlchemy. Las interfaces van en `ports/`; las implementaciones, en `adapters/`.
- **Python:** formato y lint con `ruff format` y `ruff check`.
- **TypeScript:** lint con `npm run lint`.
- **Base de datos:** todo cambio de esquema se hace con una migración de Alembic, nunca a mano.
- **Secretos:** nunca subir `.env`, contraseñas, tokens ni llaves. Usar `.env.example` y GitHub Secrets.
- **Datos:** solo datos ficticios en Local, Staging y Demo.

## Comandos útiles

```bash
# Levantar todo
docker compose up -d --build

# Aplicar migraciones
docker compose exec backend alembic upgrade head

# Crear una migración nueva
docker compose exec backend alembic revision -m "PC-<n> descripcion"

# Revisiones antes de un PR (desde backend/)
ruff format . && ruff check . && pytest -q
```
