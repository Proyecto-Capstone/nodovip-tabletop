from fastapi import FastAPI

from app import config
from app.adapters.inbound.api import (
    accesos,
    autenticacion,
    debrief,
    en_vivo,
    escenarios,
    leaderboard,
    mis_sesiones,
    monitoreo,
    reportes,
    respuestas,
    sesiones,
    usuarios,
)

config.verificar_configuracion()


def urls_documentacion(desarrollo: bool) -> dict[str, str | None]:
    """PC-47 (OWASP A05): la documentación interactiva solo en desarrollo. En
    un servidor real no se publica el mapa completo de la API."""
    if desarrollo:
        return {
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


app = FastAPI(
    title="NODOVIP Tabletop API", **urls_documentacion(config.es_desarrollo())
)

app.include_router(autenticacion.router)
app.include_router(accesos.router)
app.include_router(escenarios.router)
app.include_router(sesiones.router)
app.include_router(mis_sesiones.router)
app.include_router(en_vivo.router)
app.include_router(respuestas.router)
app.include_router(reportes.router)
app.include_router(debrief.router)
app.include_router(leaderboard.router)
app.include_router(monitoreo.router)
app.include_router(usuarios.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": config.ambiente()}
