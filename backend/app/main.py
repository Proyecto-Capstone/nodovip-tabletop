import os

from fastapi import FastAPI

from app.adapters.inbound.api import escenarios

app = FastAPI(title="NODOVIP Tabletop API")

app.include_router(escenarios.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV", "local")}
