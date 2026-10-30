"""API del reporte de brechas (PB-14) con dobles en memoria."""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import en_vivo, reportes
from app.adapters.outbound.en_vivo.memoria import EnVivoEnMemoria
from app.application.en_vivo import ServicioEnVivo
from app.application.reportes import ServicioReportes
from app.domain.escenarios import Inject, Nivel, RolEjercicio
from app.domain.sesiones import (
    EstadoSesion,
    ParticipanteSesion,
    SesionTabletop,
    TareaSesion,
)
from app.main import app
from tests.fakes import (
    GeneradorPdfFalso,
    RepoReportesEnMemoria,
    RepoRespuestasEnMemoria,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
T0 = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)


class CatalogoFalso:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI")]


class EscenariosFalsos:
    def obtener(self, escenario_id):
        return None


def _sesion(estado=EstadoSesion.FINALIZADA, moderador=ID_MODERADOR):
    i1 = Inject("Detección", "Archivos cifrados", orden=1)
    return SesionTabletop(
        nombre="Simulacro Q4",
        cliente="Banco Andino",
        escenario_id=uuid4(),
        moderador_id=moderador,
        roles=["ti"],
        injects=[i1],
        tareas=[
            TareaSesion("¿Qué hace?", "ti", Nivel.ALTO, ["Aislar"], inject_id=i1.id)
        ],
        participantes=[ParticipanteSesion(uuid4(), "ti")],
        estado=estado,
        iniciada_en=T0,
        finalizada_en=T0 + timedelta(minutes=40)
        if estado == EstadoSesion.FINALIZADA
        else None,
        inject_actual=1,
    )


@pytest.fixture
def e(sesion_por_cabecera):
    repo, generador = RepoSesionesEnMemoria(), GeneradorPdfFalso()
    almacen = EnVivoEnMemoria()
    servicio = ServicioReportes(
        repo,
        RepoRespuestasEnMemoria(),
        CatalogoFalso(),
        RepoUsuariosEnMemoria(),
        EscenariosFalsos(),
        almacen,
        RepoReportesEnMemoria(),
        generador,
    )
    app.dependency_overrides[reportes.get_servicio_reportes] = lambda: servicio
    app.dependency_overrides[en_vivo.get_servicio_en_vivo] = lambda: ServicioEnVivo(
        repo, almacen
    )
    with TestClient(app) as client:
        yield {"client": client, "repo": repo, "servicio": servicio, "gen": generador}
    app.dependency_overrides.pop(reportes.get_servicio_reportes, None)
    app.dependency_overrides.pop(en_vivo.get_servicio_en_vivo, None)


def _como(rol):
    return {"X-Rol-Prueba": rol}


@pytest.mark.parametrize("rol", ["analista", "moderador", "administrador"])
def test_analista_moderador_y_administrador_ven_el_reporte(e, rol):
    sesion = _sesion()
    e["repo"].guardar(sesion)
    r = e["client"].get(f"/api/reportes/{sesion.id}", headers=_como(rol))
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["nombre"] == "Simulacro Q4" and datos["cliente"] == "Banco Andino"
    assert datos["brechas"][0]["tipo"] == "sin_respuesta"
    assert datos["brechas"][0]["tipo_etiqueta"] == "Sin respuesta"
    assert datos["recomendaciones"] and datos["pdf"] is None
    lista = e["client"].get("/api/reportes", headers=_como(rol)).json()
    assert [x["id"] for x in lista] == [str(sesion.id)]


@pytest.mark.parametrize("rol", ["participante", "observador"])
def test_otros_roles_no_ven_reportes(e, rol):
    sesion = _sesion()
    e["repo"].guardar(sesion)
    assert e["client"].get("/api/reportes", headers=_como(rol)).status_code == 403
    r = e["client"].get(f"/api/reportes/{sesion.id}/pdf", headers=_como(rol))
    assert r.status_code == 403
    assert e["client"].get("/api/reportes").status_code == 401


def test_moderador_ajeno_o_sesion_sin_finalizar_es_404(e):
    ajena = _sesion(moderador=uuid4())
    en_curso = _sesion(estado=EstadoSesion.EN_CURSO)
    e["repo"].guardar(ajena)
    e["repo"].guardar(en_curso)
    for s in (ajena, en_curso):
        r = e["client"].get(f"/api/reportes/{s.id}", headers=_como("moderador"))
        assert r.status_code == 404
    # El analista sí ve la ajena (no la que sigue en curso).
    r = e["client"].get(f"/api/reportes/{ajena.id}", headers=_como("analista"))
    assert r.status_code == 200


def test_descarga_el_pdf_y_regenera(e):
    sesion = _sesion()
    e["repo"].guardar(sesion)
    r = e["client"].get(f"/api/reportes/{sesion.id}/pdf", headers=_como("analista"))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    estado = e["client"].get(f"/api/reportes/{sesion.id}", headers=_como("analista"))
    assert estado.json()["pdf"]["estado"] == "generado"
    r = e["client"].post(
        f"/api/reportes/{sesion.id}/regenerar", headers=_como("analista")
    )
    assert r.status_code == 200 and r.json()["estado"] == "generado"
    assert len(e["gen"].recibidos) == 2


def test_si_weasyprint_falla_responde_503_y_queda_registrado(e):
    sesion = _sesion()
    e["repo"].guardar(sesion)
    e["servicio"].generador = GeneradorPdfFalso(fallar=True)
    r = e["client"].get(f"/api/reportes/{sesion.id}/pdf", headers=_como("analista"))
    assert r.status_code == 503 and "WeasyPrint" in r.json()["detail"]
    estado = e["client"].get(f"/api/reportes/{sesion.id}", headers=_como("analista"))
    assert estado.json()["pdf"]["estado"] == "fallido"


def test_al_cerrar_la_sesion_se_programa_el_reporte(e):
    sesion = _sesion(estado=EstadoSesion.PROGRAMADA)
    sesion.iniciada_en = None
    e["repo"].guardar(sesion)
    programados = []
    app.dependency_overrides[reportes.get_tarea_reporte] = lambda: programados.append
    base = f"/api/sesiones/{sesion.id}/en-vivo"
    for accion in ("iniciar", "cerrar"):
        r = e["client"].post(f"{base}/{accion}", headers=_como("moderador"))
        assert r.status_code == 200, r.text
    assert programados == [sesion.id]
