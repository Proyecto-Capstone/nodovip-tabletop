import os

from fastapi import FastAPI

from app.adapters.inbound.api import escenarios, usuarios

app = FastAPI(title="NODOVIP Tabletop API")

app.include_router(escenarios.router)
app.include_router(usuarios.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "local")}
