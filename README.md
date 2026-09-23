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
