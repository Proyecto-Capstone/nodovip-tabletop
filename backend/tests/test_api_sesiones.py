"""Pruebas de la API del diseñador de tabletop (PB-05) con repositorios en memoria."""

import copy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.sesiones import get_servicio
from app.application.sesiones import ServicioSesiones
from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    RolEjercicio,
    Tarea,
)
from app.domain.sesiones import SesionTabletop
from app.domain.usuarios import RolNombre, Usuario
from app.main import app
from tests.fakes import RelojFalso, RepoUsuariosEnMemoria

MODERADOR = {"X-Rol-Prueba": "moderador"}
ADMIN = {"X-Rol-Prueba": "administrador"}
PARTICIPANTE = {"X-Rol-Prueba": "participante"}
ID_MODERADOR = uuid5(NAMESPACE_URL, "prueba:moderador")
AHORA = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


class RepoSesionesEnMemoria:
    def __init__(self):
        self.datos = {}

    def obtener(self, sesion_id):
        s = self.datos.get(sesion_id)
        return copy.deepcopy(s) if s else None

    def listar_por_moderador(self, moderador_id):
        return [
            copy.deepcopy(s)
            for s in self.datos.values()
            if s.moderador_id == moderador_id
        ]

    def guardar(self, sesion):
        self.datos[sesion.id] = copy.deepcopy(sesion)
        return copy.deepcopy(sesion)

    def eliminar(self, sesion_id):
        self.datos.pop(sesion_id, None)


class RepoEscenariosEnMemoria:
    def __init__(self, *escenarios):
        self.datos = {e.id: e for e in escenarios}

    def obtener(self, escenario_id):
        e = self.datos.get(escenario_id)
        return copy.deepcopy(e) if e else None


class CatalogoEnMemoria:
    def roles_ejercicio(self):
        return [
            RolEjercicio("ti", "Responsable de TI"),
            RolEjercicio("legal", "Legal"),
            RolEjercicio("ciso", "CISO"),
        ]


def _escenario(estado=EstadoEscenario.PUBLICADO) -> Escenario:
    return Escenario(
        nombre="Ransomware en sucursal",
        tipo_codigo="ransomware",
        descripcion="Cifrado de servidores con nota de rescate.",
        nivel=Nivel.ALTO,
        roles=["ti", "legal"],
        injects=[
            Inject(f"Inject {n}", "Ocurre un evento nuevo", orden=n) for n in (1, 2, 3)
        ],
        tareas=[
            Tarea("¿Cómo contiene la propagación?", "ti", Nivel.MEDIO, ["Aísla"]),
            Tarea("¿Qué obligaciones legales aplican?", "legal", Nivel.ALTO, ["Ley"]),
        ],
        estado=estado,
    )


def _usuario(rol=RolNombre.PARTICIPANTE, activo=True, nombre="Ana") -> Usuario:
    return Usuario(
        correo=f"{nombre.lower()}-{uuid4().hex[:6]}@prueba.test",
        nombre=nombre,
        password_hash="x",
        rol=rol,
        activo=activo,
    )


@pytest.fixture
def entorno(sesion_por_cabecera):
    publicado = _escenario()
    borrador = _escenario(EstadoEscenario.BORRADOR)
    usuarios = RepoUsuariosEnMemoria()
    ana, luis = _usuario(nombre="Ana"), _usuario(nombre="Luis")
    inactivo = _usuario(nombre="Inactivo", activo=False)
    moderador = _usuario(rol=RolNombre.MODERADOR, nombre="Mod")
    for u in (ana, luis, inactivo, moderador):
        usuarios.guardar(u)
    repo = RepoSesionesEnMemoria()
    servicio = ServicioSesiones(
        repo,
        RepoEscenariosEnMemoria(publicado, borrador),
        CatalogoEnMemoria(),
        usuarios,
        reloj=RelojFalso(AHORA),
    )
    app.dependency_overrides[get_servicio] = lambda: servicio
    yield {
        "client": TestClient(app),
        "repo": repo,
        "publicado": publicado,
        "borrador": borrador,
        "ana": ana,
        "luis": luis,
        "inactivo": inactivo,
        "moderador": moderador,
    }
    app.dependency_overrides.pop(get_servicio, None)


def _crear(e) -> dict:
    r = e["client"].post(
        "/api/sesiones",
        json={"escenario_id": str(e["publicado"].id)},
        headers=MODERADOR,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _diseno_completo(sesion: dict, e) -> dict:
    """Convierte el detalle devuelto en un diseño listo para programar."""
    return {
        "nombre": "Simulacro Q4",
        "roles": sesion["roles"],
        "injects": sesion["injects"],
        "tareas": sesion["tareas"],
        "participantes": [
            {"usuario_id": str(e["ana"].id), "rol_codigo": "ti"},
            {"usuario_id": str(e["luis"].id), "rol_codigo": "legal"},
        ],
        "pesos": {"completitud": 50, "precision": 30, "tiempo": 20},
        "fecha_programada": (AHORA + timedelta(days=3)).isoformat(),
        "duracion_minutos": 90,
    }


# --- Seguridad -------------------------------------------------------------------


def test_sin_sesion_responde_401(entorno):
    assert entorno["client"].get("/api/sesiones").status_code == 401


@pytest.mark.parametrize("cabecera", [ADMIN, PARTICIPANTE])
def test_solo_el_moderador_disena(entorno, cabecera):
    assert entorno["client"].get("/api/sesiones", headers=cabecera).status_code == 403


def test_un_moderador_no_ve_sesiones_de_otro(entorno):
    ajena = SesionTabletop.desde_escenario(entorno["publicado"], uuid4())
    entorno["repo"].guardar(ajena)
    client = entorno["client"]

    assert client.get(f"/api/sesiones/{ajena.id}", headers=MODERADOR).status_code == 404
    assert client.get("/api/sesiones", headers=MODERADOR).json() == []


# --- Paso 1: crear desde un escenario --------------------------------------------


def test_crear_copia_el_escenario_publicado(entorno):
    sesion = _crear(entorno)

    assert sesion["estado"] == "borrador"
    assert sesion["nombre"] == "Ransomware en sucursal"
    assert sesion["roles"] == ["ti", "legal"]
    assert len(sesion["injects"]) == 3
    assert all(t["inject_id"] for t in sesion["tareas"])
    assert sesion["puntaje_maximo_total"] == 20
    assert sesion["pesos"] == {"completitud": 40, "precision": 40, "tiempo": 20}
    assert "Debe tener fecha y hora programadas" in sesion["pendientes_para_programar"]


@pytest.mark.parametrize("clave", ["borrador", None])
def test_no_se_crea_desde_un_escenario_no_publicado(entorno, clave):
    escenario_id = entorno[clave].id if clave else uuid4()
    r = entorno["client"].post(
        "/api/sesiones", json={"escenario_id": str(escenario_id)}, headers=MODERADOR
    )
    assert r.status_code == 422


# --- Pasos 2 a 5: guardar el diseño ----------------------------------------------


def test_guardar_borrador_y_retomarlo(entorno):
    sesion = _crear(entorno)
    client = entorno["client"]
    diseno = {
        "nombre": "Simulacro Q4",
        "roles": sesion["roles"],
        "injects": sesion["injects"],
        "tareas": sesion["tareas"],
    }

    r = client.put(f"/api/sesiones/{sesion['id']}", json=diseno, headers=MODERADOR)
    assert r.status_code == 200, r.text

    retomada = client.get(f"/api/sesiones/{sesion['id']}", headers=MODERADOR).json()
    assert retomada["nombre"] == "Simulacro Q4"
    assert retomada["estado"] == "borrador"
    assert [s["nombre"] for s in client.get("/api/sesiones", headers=MODERADOR).json()]


def test_agregar_inject_y_tarea_de_seleccion_multiple(entorno):
    sesion = _crear(entorno)
    diseno = _diseno_completo(sesion, entorno)
    nuevo_inject = str(uuid4())
    diseno["injects"].append(
        {"id": nuevo_inject, "titulo": "Prensa", "descripcion": "Un medio publica"}
    )
    diseno["tareas"].append(
        {
            "inject_id": nuevo_inject,
            "rol_codigo": "legal",
            "tipo": "seleccion_multiple",
            "enunciado": "¿Se emite un comunicado oficial?",
            "opciones": [
                {"texto": "Sí, en la primera hora", "correcta": True},
                {"texto": "No"},
            ],
            "puntaje_maximo": 15,
        }
    )

    r = entorno["client"].put(
        f"/api/sesiones/{sesion['id']}", json=diseno, headers=MODERADOR
    )

    assert r.status_code == 200, r.text
    datos = r.json()
    assert [i["orden"] for i in datos["injects"]] == [1, 2, 3, 4]
    nueva = datos["tareas"][-1]
    assert nueva["inject_id"] == nuevo_inject
    assert nueva["opciones"][0] == {"texto": "Sí, en la primera hora", "correcta": True}
    assert datos["puntaje_maximo_total"] == 35
    assert datos["pendientes_para_programar"] == []


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ({"pesos": {"completitud": 50, "precision": 50, "tiempo": 20}}, "sumar 100"),
        ({"roles": ["ti", "legal", "inventado"]}, "Roles desconocidos"),
    ],
)
def test_diseno_invalido_responde_422(entorno, cambio, mensaje):
    sesion = _crear(entorno)
    diseno = _diseno_completo(sesion, entorno) | cambio

    r = entorno["client"].put(
        f"/api/sesiones/{sesion['id']}", json=diseno, headers=MODERADOR
    )
    assert r.status_code == 422
    assert any(mensaje in e for e in r.json()["detail"]["errores"])


@pytest.mark.parametrize("clave", ["inactivo", "moderador"])
def test_solo_se_asignan_participantes_activos(entorno, clave):
    sesion = _crear(entorno)
    diseno = _diseno_completo(sesion, entorno)
    diseno["participantes"][0]["usuario_id"] = str(entorno[clave].id)

    r = entorno["client"].put(
        f"/api/sesiones/{sesion['id']}", json=diseno, headers=MODERADOR
    )
    assert r.status_code == 422
    assert "participantes activos" in r.json()["detail"]["errores"][0]


def test_participantes_disponibles_solo_activos_con_rol_participante(entorno):
    r = entorno["client"].get(
        "/api/sesiones/participantes-disponibles", headers=MODERADOR
    )
    assert r.status_code == 200
    assert sorted(u["nombre"] for u in r.json()) == ["Ana", "Luis"]
    assert set(r.json()[0]) == {"id", "nombre", "correo"}


# --- Programar y eliminar --------------------------------------------------------


def test_programar_sesion_completa(entorno):
    sesion = _crear(entorno)
    client = entorno["client"]
    url = f"/api/sesiones/{sesion['id']}"
    client.put(url, json=_diseno_completo(sesion, entorno), headers=MODERADOR)

    r = client.post(f"{url}/programar", headers=MODERADOR)

    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "programada"
    # Una sesión programada ya no se elimina.
    assert client.delete(url, headers=MODERADOR).status_code == 422


def test_programar_incompleta_lista_lo_que_falta(entorno):
    sesion = _crear(entorno)

    r = entorno["client"].post(
        f"/api/sesiones/{sesion['id']}/programar", headers=MODERADOR
    )

    assert r.status_code == 422
    errores = r.json()["detail"]["errores"]
    assert "Falta al menos un participante para los roles: ti, legal" in errores
    assert "Debe tener una duración" in errores


def test_fecha_sin_zona_horaria_se_rechaza(entorno):
    sesion = _crear(entorno)
    diseno = _diseno_completo(sesion, entorno)
    diseno["fecha_programada"] = "2026-10-25T09:00:00"

    r = entorno["client"].put(
        f"/api/sesiones/{sesion['id']}", json=diseno, headers=MODERADOR
    )
    assert r.status_code == 422


def test_eliminar_un_borrador(entorno):
    sesion = _crear(entorno)
    url = f"/api/sesiones/{sesion['id']}"

    assert entorno["client"].delete(url, headers=MODERADOR).status_code == 204
    assert entorno["client"].get(url, headers=MODERADOR).status_code == 404
