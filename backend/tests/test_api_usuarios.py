"""API de gestión de usuarios (PB-02) con repositorio en memoria.

No necesita PostgreSQL: corre igual en local y en el CI.
"""

import copy

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.usuarios import get_servicio_usuarios
from app.application.usuarios import ServicioUsuarios
from app.domain.usuarios import RolNombre
from app.main import app
from app.ports.usuario_repository import FiltroUsuarios

ADMIN = {"X-Rol-Debug": "administrador"}
MODERADOR = {"X-Rol-Debug": "moderador"}
CLAVE = "Nodovip2026seguro"


class RepoEnMemoria:
    def __init__(self):
        self.datos = {}

    def obtener_por_id(self, usuario_id):
        u = self.datos.get(usuario_id)
        return copy.deepcopy(u) if u else None

    def obtener_por_correo(self, correo):
        for u in self.datos.values():
            if u.correo.lower() == correo.lower():
                return copy.deepcopy(u)
        return None

    def listar(self, filtro: FiltroUsuarios | None = None):
        filtro = filtro or FiltroUsuarios()
        res = list(self.datos.values())
        if filtro.texto:
            t = filtro.texto.lower()
            res = [u for u in res if t in (u.nombre + u.correo).lower()]
        if filtro.rol:
            res = [u for u in res if u.rol == filtro.rol]
        if filtro.activo is not None:
            res = [u for u in res if u.activo == filtro.activo]
        return [copy.deepcopy(u) for u in sorted(res, key=lambda u: u.nombre)]

    def contar_activos(self, rol):
        return sum(1 for u in self.datos.values() if u.rol == rol and u.activo)

    def guardar(self, usuario):
        self.datos[usuario.id] = copy.deepcopy(usuario)
        return copy.deepcopy(usuario)

    def eliminar(self, usuario_id):
        self.datos.pop(usuario_id, None)


class HasherFalso:
    def hashear(self, contrasena):
        return f"hash::{contrasena[::-1]}"

    def verificar(self, contrasena, hash_guardado):
        return hash_guardado == self.hashear(contrasena)


@pytest.fixture
def repo():
    return RepoEnMemoria()


@pytest.fixture
def client(monkeypatch, repo):
    monkeypatch.setenv("APP_ENV", "test")
    servicio = ServicioUsuarios(repo, HasherFalso())
    app.dependency_overrides[get_servicio_usuarios] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def _crear(client, nombre="Ana Pérez", correo="ana@example.com", rol="moderador"):
    r = client.post(
        "/api/usuarios",
        json={"nombre": nombre, "correo": correo, "contrasena": CLAVE, "rol": rol},
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- Seguridad ---------------------------------------------------------------------


def test_sin_usuario_401(client):
    assert client.get("/api/usuarios").status_code == 401


def test_moderador_no_gestiona_usuarios(client):
    assert client.get("/api/usuarios", headers=MODERADOR).status_code == 403
    r = client.post(
        "/api/usuarios",
        json={
            "nombre": "X Y Z",
            "correo": "x@example.com",
            "contrasena": CLAVE,
            "rol": "participante",
        },
        headers=MODERADOR,
    )
    assert r.status_code == 403


def test_respuesta_no_incluye_la_contrasena(client, repo):
    creado = _crear(client)
    assert "contrasena" not in creado
    assert "password_hash" not in creado
    guardado = next(iter(repo.datos.values()))
    assert guardado.password_hash != CLAVE


# --- Crear y validar ---------------------------------------------------------------


def test_crear_normaliza_el_correo(client):
    creado = _crear(client, correo="  Ana@Example.COM ")
    assert creado["correo"] == "ana@example.com"
    assert creado["activo"] is True
    assert creado["rol"] == "moderador"


def test_correo_duplicado_409(client):
    _crear(client)
    r = client.post(
        "/api/usuarios",
        json={
            "nombre": "Otra Ana",
            "correo": "ANA@example.com",
            "contrasena": CLAVE,
            "rol": "analista",
        },
        headers=ADMIN,
    )
    assert r.status_code == 409


def test_correo_invalido_422(client):
    r = client.post(
        "/api/usuarios",
        json={
            "nombre": "Ana Pérez",
            "correo": "no-es-correo",
            "contrasena": CLAVE,
            "rol": "analista",
        },
        headers=ADMIN,
    )
    assert r.status_code == 422


def test_contrasena_debil_422(client):
    r = client.post(
        "/api/usuarios",
        json={
            "nombre": "Ana Pérez",
            "correo": "ana@example.com",
            "contrasena": "debil",
            "rol": "analista",
        },
        headers=ADMIN,
    )
    assert r.status_code == 422
    assert "Contraseña" in str(r.json())


def test_rol_inexistente_422(client):
    r = client.post(
        "/api/usuarios",
        json={
            "nombre": "Ana Pérez",
            "correo": "ana@example.com",
            "contrasena": CLAVE,
            "rol": "superusuario",
        },
        headers=ADMIN,
    )
    assert r.status_code == 422


# --- Listar, editar, desactivar ----------------------------------------------------


def test_listar_con_filtros(client):
    _crear(client, nombre="Ana Pérez", correo="ana@example.com", rol="moderador")
    _crear(client, nombre="Luis Mora", correo="luis@example.com", rol="analista")
    get = client.get
    assert len(get("/api/usuarios", headers=ADMIN).json()) == 2
    assert len(get("/api/usuarios?q=luis", headers=ADMIN).json()) == 1
    assert len(get("/api/usuarios?rol=moderador", headers=ADMIN).json()) == 1
    assert len(get("/api/usuarios?activo=false", headers=ADMIN).json()) == 0


def test_cambiar_rol_y_datos(client):
    creado = _crear(client)
    r = client.put(
        f"/api/usuarios/{creado['id']}",
        json={
            "nombre": "Ana Pérez Ruiz",
            "correo": "ana@example.com",
            "rol": "observador",
        },
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert r.json()["rol"] == "observador"
    assert r.json()["nombre"] == "Ana Pérez Ruiz"


def test_cambiar_a_correo_de_otro_usuario_409(client):
    _crear(client, correo="ana@example.com")
    luis = _crear(client, nombre="Luis Mora", correo="luis@example.com")
    r = client.put(
        f"/api/usuarios/{luis['id']}",
        json={"nombre": "Luis Mora", "correo": "ana@example.com", "rol": "moderador"},
        headers=ADMIN,
    )
    assert r.status_code == 409


def test_desactivar_y_activar(client):
    creado = _crear(client)
    r = client.post(f"/api/usuarios/{creado['id']}/desactivar", headers=ADMIN)
    assert r.json()["activo"] is False
    r = client.post(f"/api/usuarios/{creado['id']}/activar", headers=ADMIN)
    assert r.json()["activo"] is True


def test_no_se_desactiva_al_ultimo_administrador(client):
    admin = _crear(
        client, nombre="Admin Único", correo="admin@example.com", rol="administrador"
    )
    r = client.post(f"/api/usuarios/{admin['id']}/desactivar", headers=ADMIN)
    assert r.status_code == 422
    assert "último administrador" in str(r.json())
    r = client.put(
        f"/api/usuarios/{admin['id']}",
        json={
            "nombre": "Admin Único",
            "correo": "admin@example.com",
            "rol": "moderador",
        },
        headers=ADMIN,
    )
    assert r.status_code == 422


def test_con_dos_administradores_si_se_puede_desactivar_uno(client):
    a = _crear(client, nombre="Admin Uno", correo="a1@example.com", rol="administrador")
    _crear(client, nombre="Admin Dos", correo="a2@example.com", rol="administrador")
    r = client.post(f"/api/usuarios/{a['id']}/desactivar", headers=ADMIN)
    assert r.status_code == 200


def test_restablecer_contrasena(client, repo):
    creado = _crear(client)
    antes = next(iter(repo.datos.values())).password_hash
    r = client.post(
        f"/api/usuarios/{creado['id']}/contrasena",
        json={"contrasena": "OtraClave2026x"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert next(iter(repo.datos.values())).password_hash != antes
    r = client.post(
        f"/api/usuarios/{creado['id']}/contrasena",
        json={"contrasena": "corta"},
        headers=ADMIN,
    )
    assert r.status_code == 422


def test_no_se_elimina_una_cuenta_activa(client):
    creado = _crear(client)
    r = client.delete(f"/api/usuarios/{creado['id']}", headers=ADMIN)
    assert r.status_code == 422
    assert "desactiva" in str(r.json())


def test_eliminar_cuenta_desactivada(client):
    creado = _crear(client)
    client.post(f"/api/usuarios/{creado['id']}/desactivar", headers=ADMIN)
    r = client.delete(f"/api/usuarios/{creado['id']}", headers=ADMIN)
    assert r.status_code == 204
    assert client.get(f"/api/usuarios/{creado['id']}", headers=ADMIN).status_code == 404


def test_moderador_no_elimina(client):
    creado = _crear(client)
    r = client.delete(f"/api/usuarios/{creado['id']}", headers=MODERADOR)
    assert r.status_code == 403


def test_usuario_inexistente_404(client):
    r = client.get("/api/usuarios/00000000-0000-0000-0000-000000000000", headers=ADMIN)
    assert r.status_code == 404


def test_roles_validos_son_los_del_sistema():
    assert {r.value for r in RolNombre} == {
        "administrador",
        "moderador",
        "participante",
        "observador",
        "analista",
    }
