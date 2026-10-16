from fastapi import FastAPI

from app import config
from app.adapters.inbound.api import accesos, autenticacion, escenarios, usuarios

config.verificar_configuracion()

app = FastAPI(title="NODOVIP Tabletop API")

app.include_router(autenticacion.router)
app.include_router(accesos.router)
app.include_router(escenarios.router)
app.include_router(usuarios.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": config.ambiente()}
