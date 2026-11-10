from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde_ok():
    response = client.get("/health")
    assert response.status_code == 200


def test_la_documentacion_de_la_api_solo_se_publica_en_desarrollo():
    """PC-47 (OWASP A05): en Staging/Demo no se expone /docs ni /openapi.json."""
    from fastapi import FastAPI

    from app.main import urls_documentacion

    servidor = TestClient(FastAPI(**urls_documentacion(desarrollo=False)))
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert servidor.get(ruta).status_code == 404
    local = TestClient(FastAPI(**urls_documentacion(desarrollo=True)))
    assert local.get("/openapi.json").status_code == 200
