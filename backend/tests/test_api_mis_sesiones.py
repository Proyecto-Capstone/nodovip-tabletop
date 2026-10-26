"""API del participante (PB-06) e invitaciones del moderador, con dobles en memoria."""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api import mis_sesiones, sesiones
from app.application.invitaciones import ServicioInvitaciones
from app.application.sesiones import ServicioSesiones
from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    RolEjercicio,
    Tarea,
)
from app.domain.sesiones import ParticipanteSesion, SesionTabletop
from app.domain.usuarios import RolNombre, Usuario
from app.main import app
from tests.fakes import (
    EnviadorFalso,
    RelojFalso,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

MODERADOR = {"X-Rol-Prueba": "moderador"}
PARTICIPANTE = {"X-Rol-Prueba": "participante"}
OBSERVADOR = {"X-Rol-Prueba": "observador"}
# La fixture sesion_por_cabecera usa estos id para los usuarios de prueba.
ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
ID_PARTICIPANTE = uuid5(NAMESPACE_URL, "prueba:participante")
AHORA = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)


class RepoEscenarios:
    def __init__(self, escenario):
        self.escenario = escenario

    def obtener(self, escenario_id):
        return self.escenario if escenario_id == self.escenario.id else None


class Catalogo:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


@pytest.fixture
def entorno(sesion_por_cabecera):
    escenario = Escenario(
        nombre="Ransomware en sucursal",
        tipo_codigo="ransomware",
        descripcion="Cifrado de los servidores de archivos.",
        nivel=Nivel.ALTO,
        roles=["ti", "legal"],
        injects=[Inject("Inject 1", "Detalle del inject", orden=1)],
        tareas=[
            Tarea("¿Qué aísla primero?", "ti", Nivel.MEDIO, ["Segmenta"]),
            Tarea("¿A quién notifica?", "legal", Nivel.BAJO, ["Regulador"]),
        ],
        estado=EstadoEscenario.PUBLICADO,
    )
    usuarios = RepoUsuariosEnMemoria()
    for uid, nombre, rol in [
        (ID_MODERADOR, "Mónica", RolNombre.MODERADOR),
        (ID_PARTICIPANTE, "Ana", RolNombre.PARTICIPANTE),
    ]:
        usuarios.guardar(
            Usuario(f"{nombre.lower()}@prueba.test", nombre, "x", rol, id=uid)
        )
    luis = usuarios.guardar(
        Usuario("luis@prueba.test", "Luis", "x", RolNombre.PARTICIPANTE)
    )
    repo = RepoSesionesEnMemoria()
    enviador = EnviadorFalso()
    reloj = RelojFalso(AHORA)
    invitaciones = ServicioInvitaciones(
        repo,
        Catalogo(),
        usuarios,
        enviador,
        "http://localhost:8080",
        reloj=reloj,
        escenarios=RepoEscenarios(escenario),
    )
    servicio_sesiones = ServicioSesiones(
        repo,
        RepoEscenarios(escenario),
        Catalogo(),
        usuarios,
        reloj=reloj,
        invitar=invitaciones.enviar_pendientes,
    )
    sesion = SesionTabletop.desde_escenario(escenario, ID_MODERADOR, "Simulacro Q4")
    sesion.participantes = [
        ParticipanteSesion(ID_PARTICIPANTE, "ti"),
        ParticipanteSesion(luis.id, "legal"),
    ]
    sesion.fecha_programada = AHORA + timedelta(days=2)
    sesion.duracion_minutos = 90
    repo.guardar(sesion)

    app.dependency_overrides[sesiones.get_servicio] = lambda: servicio_sesiones
    app.dependency_overrides[mis_sesiones.get_servicio] = lambda: invitaciones
    yield {
        "client": TestClient(app),
        "sesion": sesion,
        "repo": repo,
        "enviador": enviador,
        "luis": luis,
    }
    app.dependency_overrides.pop(sesiones.get_servicio, None)
    app.dependency_overrides.pop(mis_sesiones.get_servicio, None)


def _programar(entorno):
    r = entorno["client"].post(
        f"/api/sesiones/{entorno['sesion'].id}/programar", headers=MODERADOR
    )
    assert r.status_code == 200, r.text
    return r.json()


# --- Moderador --------------------------------------------------------------------


def test_programar_envia_invitaciones_y_el_moderador_ve_su_estado(entorno):
    datos = _programar(entorno)

    assert len(entorno["enviador"].enviados) == 2
    estados = {p["rol_codigo"]: p["invitacion"] for p in datos["participantes"]}
    assert estados == {"ti": "enviada", "legal": "enviada"}
    assert datos["participantes"][0]["invitacion_enviada_en"] is not None


def test_reenviar_desde_el_paso_6(entorno):
    entorno["enviador"].fallar_para = {"luis@prueba.test"}
    datos = _programar(entorno)
    legal = next(p for p in datos["participantes"] if p["rol_codigo"] == "legal")
    assert legal["invitacion"] == "fallida"
    assert "invalid email" in legal["invitacion_error"]

    entorno["enviador"].fallar_para = set()
    r = entorno["client"].post(
        f"/api/sesiones/{entorno['sesion'].id}/invitaciones", headers=MODERADOR
    )

    assert r.status_code == 200
    estados = {p["rol_codigo"]: p["invitacion"] for p in r.json()["participantes"]}
    assert estados == {"ti": "enviada", "legal": "enviada"}


def test_reenviar_un_borrador_responde_422(entorno):
    r = entorno["client"].post(
        f"/api/sesiones/{entorno['sesion'].id}/invitaciones", headers=MODERADOR
    )
    assert r.status_code == 422


# --- Participante -----------------------------------------------------------------


def test_sin_sesion_401_y_otros_roles_403(entorno):
    client = entorno["client"]
    assert client.get("/api/mis-sesiones").status_code == 401
    assert client.get("/api/mis-sesiones", headers=OBSERVADOR).status_code == 403
    assert client.get("/api/mis-sesiones", headers=MODERADOR).status_code == 403


def test_el_participante_ve_su_sesion_programada_sin_tareas(entorno):
    client = entorno["client"]
    assert client.get("/api/mis-sesiones", headers=PARTICIPANTE).json() == []

    _programar(entorno)
    [s] = client.get("/api/mis-sesiones", headers=PARTICIPANTE).json()

    assert s["nombre"] == "Simulacro Q4"
    assert s["rol_codigo"] == "ti"
    assert s["rol_nombre"] == "Responsable de TI"
    assert s["moderador_nombre"] == "Mónica"
    assert s["escenario_nombre"] == "Ransomware en sucursal"
    assert s["invitacion"] == "enviada"
    # Nada de tareas, opciones ni criterios: llegan en vivo con PB-08.
    assert "tareas" not in s and "injects" not in s


def test_detalle_y_aceptar(entorno):
    _programar(entorno)
    client = entorno["client"]
    url = f"/api/mis-sesiones/{entorno['sesion'].id}"

    assert client.get(url, headers=PARTICIPANTE).json()["invitacion"] == "enviada"
    r = client.post(f"{url}/aceptar", headers=PARTICIPANTE)

    assert r.status_code == 200
    assert r.json()["invitacion"] == "aceptada"
    assert r.json()["invitacion_aceptada_en"] is not None
    # El moderador ve la aceptación.
    moderador = client.get(f"/api/sesiones/{entorno['sesion'].id}", headers=MODERADOR)
    ti = next(p for p in moderador.json()["participantes"] if p["rol_codigo"] == "ti")
    assert ti["invitacion"] == "aceptada"


def test_una_sesion_ajena_responde_404(entorno):
    sesion = entorno["sesion"]
    # Ana sale de la sesión: ya no puede verla ni aceptarla.
    sesion.participantes = [ParticipanteSesion(entorno["luis"].id, "legal")]
    sesion.roles = ["legal"]
    sesion.tareas = [t for t in sesion.tareas if t.rol_codigo == "legal"]
    sesion.programar(AHORA)
    entorno["repo"].guardar(sesion)

    client = entorno["client"]
    url = f"/api/mis-sesiones/{sesion.id}"
    assert client.get(url, headers=PARTICIPANTE).status_code == 404
    assert client.post(f"{url}/aceptar", headers=PARTICIPANTE).status_code == 404
