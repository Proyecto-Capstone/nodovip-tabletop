"""Pruebas de la API de escenarios (PB-03 y PB-04) con repositorios en memoria.

No necesitan PostgreSQL: se reemplaza el servicio por uno con repositorios
falsos, así corren igual en local y en el CI.
"""

import copy
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.escenarios import get_servicio
from app.application.escenarios import ServicioEscenarios
from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Nivel,
    RolEjercicio,
    TipoEscenario,
)
from app.main import app
from app.ports.escenario_repository import (
    FiltroBanco,
    FiltroEscenarios,
    TareaDelBanco,
)

ADMIN = {"X-Rol-Debug": "administrador"}
MODERADOR = {"X-Rol-Debug": "moderador"}
PARTICIPANTE = {"X-Rol-Debug": "participante"}


class RepoEnMemoria:
    def __init__(self):
        self.datos: dict[UUID, Escenario] = {}

    def obtener(self, escenario_id):
        e = self.datos.get(escenario_id)
        return copy.deepcopy(e) if e else None

    def listar(self, filtro: FiltroEscenarios):
        res = list(self.datos.values())
        if filtro.texto:
            t = filtro.texto.lower()
            res = [e for e in res if t in (e.nombre + e.descripcion).lower()]
        if filtro.tipo_codigo:
            res = [e for e in res if e.tipo_codigo == filtro.tipo_codigo]
        if filtro.nivel:
            res = [e for e in res if e.nivel == filtro.nivel]
        if filtro.rol_codigo:
            res = [e for e in res if filtro.rol_codigo in e.roles]
        if filtro.estados:
            res = [e for e in res if e.estado in filtro.estados]
        return [copy.deepcopy(e) for e in sorted(res, key=lambda e: e.nombre)]

    def guardar(self, escenario):
        self.datos[escenario.id] = copy.deepcopy(escenario)
        return copy.deepcopy(escenario)

    def buscar_tareas(self, filtro: FiltroBanco):
        res = []
        for e in self.datos.values():
            if filtro.solo_publicados and e.estado != EstadoEscenario.PUBLICADO:
                continue
            if filtro.tipo_codigo and e.tipo_codigo != filtro.tipo_codigo:
                continue
            for t in e.tareas:
                if filtro.rol_codigo and t.rol_codigo != filtro.rol_codigo:
                    continue
                if filtro.dificultad and t.dificultad != filtro.dificultad:
                    continue
                res.append(TareaDelBanco(t, e.id, e.nombre, e.tipo_codigo))
        return res


class CatalogoEnMemoria:
    def tipos_escenario(self):
        return [
            TipoEscenario("ransomware", "Ransomware", "Cifrado", Nivel.ALTO, ["ti"]),
            TipoEscenario("ddos", "Ataque DDoS", "Saturación", Nivel.MEDIO, ["ti"]),
        ]

    def roles_ejercicio(self):
        return [
            RolEjercicio("ti", "Responsable de TI"),
            RolEjercicio("legal", "Legal"),
            RolEjercicio("ciso", "CISO"),
        ]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    servicio = ServicioEscenarios(RepoEnMemoria(), CatalogoEnMemoria())
    app.dependency_overrides[get_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def _payload(**cambios):
    datos = {
        "nombre": "Ransomware de prueba",
        "tipo_codigo": "ransomware",
        "descripcion": "Cifrado de servidores con nota de rescate en cada carpeta.",
        "nivel": "alto",
        "roles": ["ti", "legal"],
        "injects": [
            {"titulo": f"Inject {n}", "descripcion": "Ocurre un evento nuevo"}
            for n in range(1, 4)
        ],
        "tareas": [
            {
                "enunciado": "¿Cómo contiene la propagación?",
                "rol_codigo": "ti",
                "dificultad": "medio",
                "criterios": ["Aísla la red"],
            },
            {
                "enunciado": "¿Qué obligaciones legales aplican?",
                "rol_codigo": "legal",
                "dificultad": "alto",
                "criterios": ["Notifica a la autoridad"],
            },
        ],
    }
    datos.update(cambios)
    return datos


def _crear_y_publicar(client, **cambios) -> str:
    r = client.post("/api/escenarios", json=_payload(**cambios), headers=ADMIN)
    assert r.status_code == 201, r.text
    escenario_id = r.json()["id"]
    r = client.post(f"/api/escenarios/{escenario_id}/publicar", headers=ADMIN)
    assert r.status_code == 200, r.text
    return escenario_id


# --- Seguridad -----------------------------------------------------------------


def test_sin_usuario_responde_401(client):
    assert client.get("/api/escenarios").status_code == 401


def test_rol_debug_no_funciona_fuera_de_local_y_test(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert client.get("/api/escenarios", headers=ADMIN).status_code == 401


def test_moderador_no_puede_crear(client):
    r = client.post("/api/escenarios", json=_payload(), headers=MODERADOR)
    assert r.status_code == 403


def test_participante_no_ve_la_biblioteca(client):
    assert client.get("/api/escenarios", headers=PARTICIPANTE).status_code == 403


# --- PB-03 ---------------------------------------------------------------------


def test_admin_crea_borrador_con_injects_ordenados(client):
    r = client.post("/api/escenarios", json=_payload(), headers=ADMIN)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["estado"] == "borrador"
    assert [i["orden"] for i in cuerpo["injects"]] == [1, 2, 3]
    assert cuerpo["pendientes_para_publicar"] == []


def test_validacion_de_campos(client):
    r = client.post("/api/escenarios", json=_payload(nombre="ab"), headers=ADMIN)
    assert r.status_code == 422


def test_tipo_desconocido_se_rechaza(client):
    r = client.post(
        "/api/escenarios", json=_payload(tipo_codigo="inventado"), headers=ADMIN
    )
    assert r.status_code == 422
    assert "Tipo de escenario desconocido" in str(r.json())


def test_no_publica_con_dos_injects(client):
    payload = _payload(injects=_payload()["injects"][:2])
    escenario_id = client.post("/api/escenarios", json=payload, headers=ADMIN).json()[
        "id"
    ]
    r = client.post(f"/api/escenarios/{escenario_id}/publicar", headers=ADMIN)
    assert r.status_code == 422
    assert "al menos 3 injects" in str(r.json())


def test_admin_actualiza_y_conserva_id_de_tarea(client):
    creado = client.post("/api/escenarios", json=_payload(), headers=ADMIN).json()
    tareas = _payload()["tareas"]
    tareas[0]["id"] = creado["tareas"][0]["id"]
    tareas[0]["enunciado"] = "¿Cómo aísla los equipos afectados?"
    r = client.put(
        f"/api/escenarios/{creado['id']}",
        json=_payload(tareas=tareas),
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert r.json()["tareas"][0]["id"] == creado["tareas"][0]["id"]
    assert r.json()["tareas"][0]["enunciado"].startswith("¿Cómo aísla")


def test_archivar_lo_saca_de_la_biblioteca(client):
    escenario_id = _crear_y_publicar(client)
    r = client.post(f"/api/escenarios/{escenario_id}/archivar", headers=ADMIN)
    assert r.json()["estado"] == "archivado"
    assert client.get("/api/escenarios", headers=MODERADOR).json() == []


# --- PB-04 ---------------------------------------------------------------------


def test_moderador_solo_ve_publicados(client):
    _crear_y_publicar(client, nombre="Publicado")
    client.post("/api/escenarios", json=_payload(nombre="Borrador"), headers=ADMIN)
    nombres_mod = [
        e["nombre"] for e in client.get("/api/escenarios", headers=MODERADOR).json()
    ]
    nombres_admin = [
        e["nombre"] for e in client.get("/api/escenarios", headers=ADMIN).json()
    ]
    assert nombres_mod == ["Publicado"]
    assert nombres_admin == ["Borrador", "Publicado"]


def test_moderador_no_ve_detalle_de_borrador(client):
    r = client.post("/api/escenarios", json=_payload(), headers=ADMIN)
    escenario_id = r.json()["id"]
    r = client.get(f"/api/escenarios/{escenario_id}", headers=MODERADOR)
    assert r.status_code == 404


def test_busqueda_y_filtros(client):
    _crear_y_publicar(client, nombre="Ransomware hospital")
    _crear_y_publicar(
        client,
        nombre="Caída de la tienda en línea",
        tipo_codigo="ddos",
        nivel="medio",
    )
    get = client.get
    assert len(get("/api/escenarios?q=hospital", headers=MODERADOR).json()) == 1
    assert len(get("/api/escenarios?tipo=ddos", headers=MODERADOR).json()) == 1
    assert len(get("/api/escenarios?nivel=alto", headers=MODERADOR).json()) == 1
    assert len(get("/api/escenarios?rol=legal", headers=MODERADOR).json()) == 2


def test_detalle_para_el_moderador(client):
    escenario_id = _crear_y_publicar(client)
    r = client.get(f"/api/escenarios/{escenario_id}", headers=MODERADOR)
    assert r.status_code == 200
    assert len(r.json()["injects"]) == 3
    assert {t["rol_codigo"] for t in r.json()["tareas"]} == {"ti", "legal"}


def test_banco_de_preguntas_filtra_por_rol_y_dificultad(client):
    _crear_y_publicar(client)
    r = client.get("/api/banco-preguntas?rol=legal&dificultad=alto", headers=MODERADOR)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["escenario_nombre"] == "Ransomware de prueba"


def test_catalogos(client):
    tipos = client.get("/api/catalogos/tipos-escenario", headers=MODERADOR).json()
    roles = client.get("/api/catalogos/roles-ejercicio", headers=MODERADOR).json()
    assert {t["codigo"] for t in tipos} == {"ransomware", "ddos"}
    assert len(roles) == 3
