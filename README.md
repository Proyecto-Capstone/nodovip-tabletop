# NODOVIP Tabletop

Plataforma de ejercicios tabletop de ciberseguridad para NODOVIP.

## Estructura

- `frontend/`: React + TypeScript (Vite)
- `backend/`: FastAPI con arquitectura hexagonal
  - `app/domain/`: entidades y reglas de negocio
  - `app/ports/`: interfaces (puertos)
  - `app/adapters/inbound/`: API HTTP
  - `app/adapters/outbound/`: persistencia y servicios externos

## Requisitos

- Node.js 20 o superior
- Python 3.11 o superior

## Levantar el proyecto en local

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API disponible en http://localhost:8000 (verificación: http://localhost:8000/health). Documentación interactiva en http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplicación disponible en http://localhost:5173.

## Flujo de ramas

- `main`: versión estable
- `develop`: integración
- `feature/PC-XX-descripcion`: una rama por ticket de Jira

Los cambios entran a `develop` y `main` solo mediante pull request.

## Docker Compose

Todo el stack (frontend, backend, PostgreSQL, Redis y NGINX) se levanta con Docker Compose.

Antes de la primera ejecución, crea el archivo de variables a partir de la plantilla:

```bash
cp .env.example .env
```

El archivo `.env` contiene credenciales y no se versiona.

### Ambientes

| Ambiente | Archivos | Características |
|---|---|---|
| Local | `docker-compose.yml` + `docker-compose.override.yml` | Hot reload en frontend y backend, puertos de PostgreSQL (5432), Redis (6379) y API (8000) expuestos |
| Testing/Staging | `docker-compose.yml` + `docker-compose.staging.yml` | Build de producción, reinicio automático, logs en modo debug |
| Producción/Demo | `docker-compose.yml` + `docker-compose.prod.yml` | Build de producción, reinicio automático, 2 workers en la API, solo NGINX expuesto |

### Comandos

```bash
# Local
docker compose up --build

# Testing/Staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d --build

# Producción/Demo
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Para staging y producción, crea `.env.staging` o `.env.production` a partir de `.env.example`, con `APP_ENV` y contraseñas propias de cada ambiente.

### URLs

- Aplicación: http://localhost:8080
- Verificación de la API: http://localhost:8080/api/health
- Documentación de la API (solo local): http://localhost:8000/docs
