"""API de autenticación e historial de accesos (PB-01) con la sesión REAL.

A diferencia del resto de pruebas de API, aquí no se reemplaza
`obtener_usuario_actual`: se inicia sesión, viaja la cookie y se valida el JWT.
Solo los repositorios y el hasher son dobles en memoria.
"""

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound.api.escenarios import get_servicio as get_servicio_escenarios
from app.adapters.inbound.api.seguridad import NOMBRE_COOKIE, get_servicio_autenticacion
from app.adapters.inbound.api.usuarios import get_servicio_usuarios
from app.adapters.outbound.seguridad.jwt_tokens import JwtTokens
from app.application.autenticacion import ServicioAutenticacion
from app.application.usuarios import ServicioUsuarios
from app.domain.autenticacion import MAX_INTENTOS_FALLIDOS
from app.domain.usuarios import RolNombre, Usuario
from app.main import app
from tests.fakes import (
    HasherFalso,
    RelojFalso,
    RepoAccesosEnMemoria,
    RepoUsuariosEnMemoria,
)

CLAVE = "Nodovip2026seguro"
SECRETO = "secreto-de-prueba-de-al-menos-32-caracteres"
MENSAJE = "Correo o contraseña incorrectos"


@pytest.fixture
def usuarios():
    return RepoUsuariosEnMemoria()


@pytest.fixture
def accesos():
    return RepoAccesosEnMemoria()


@pytest.fixture
def client(usuarios, accesos):
    hasher = HasherFalso()
    autenticacion = ServicioAutenticacion(
        usuarios, accesos, hasher, JwtTokens(SECRETO), reloj=RelojFalso()
    )
    app.dependency_overrides[get_servicio_autenticacion] = lambda: autenticacion
    app.dependency_overrides[get_servicio_usuarios] = lambda: ServicioUsuarios(
        usuarios, hasher
    )
    # Escenarios no se usa: basta con que la dependencia no abra la base.
    app.dependency_overrides[get_servicio_escenarios] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _usuario(usuarios, correo, rol, activo=True):
    return usuarios.guardar(
        Usuario(
            correo=correo,
            nombre=correo.split("@")[0].title(),
            password_hash=HasherFalso().hashear(CLAVE),
            rol=rol,
            activo=activo,
        )
    )


@pytest.fixture
def admin(usuarios):
    return _usuario(usuarios, "admin@example.com", RolNombre.ADMINISTRADOR)


@pytest.fixture
def moderador(usuarios):
    return _usuario(usuarios, "mod@example.com", RolNombre.MODERADOR)


def _login(client, correo, contrasena=CLAVE):
    return client.post(
        "/api/auth/login", json={"correo": correo, "contrasena": contrasena}
    )


# --- Login ------------------------------------------------------------------------


def test_login_correcto_devuelve_usuario_y_permisos(client, admin):
    r = _login(client, "Admin@Example.com ")
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["id"] == str(admin.id)
    assert datos["rol"] == "administrador"
    assert "usuarios:gestionar" in datos["permisos"]
    assert "password_hash" not in datos and "token" not in datos


def test_login_deja_cookie_httponly_y_samesite_strict(client, admin):
    r = _login(client, "admin@example.com")
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{NOMBRE_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie
    # En APP_ENV=test no hay HTTPS; fuera de local/test va con Secure.
    assert "Secure" not in cookie


def test_mismo_mensaje_para_clave_correo_e_inactivo(client, admin, usuarios):
    _usuario(usuarios, "inactivo@example.com", RolNombre.ANALISTA, activo=False)
    intentos = [
        _login(client, "admin@example.com", "ClaveIncorrecta1"),
        _login(client, "nadie@example.com"),
        _login(client, "inactivo@example.com"),
        _login(client, "esto no es un correo"),
    ]
    for r in intentos:
        assert r.status_code == 401
        assert r.json() == {"detail": MENSAJE}
        assert "set-cookie" not in r.headers


def test_login_valida_el_cuerpo(client):
    r = client.post("/api/auth/login", json={"correo": "a@example.com"})
    assert r.status_code == 422
    r = client.post(
        "/api/auth/login", json={"correo": "a@example.com", "contrasena": "x" * 129}
    )
    assert r.status_code == 422


def test_login_exige_json(client, admin):
    # Un formulario de otro sitio (CSRF) no puede enviar JSON sin CORS.
    r = client.post(
        "/api/auth/login",
        content=f"correo=admin@example.com&contrasena={CLAVE}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 422


def test_cada_intento_queda_en_el_historial(client, admin, accesos):
    _login(client, "admin@example.com", "ClaveIncorrecta1")
    client.post(
        "/api/auth/login",
        json={"correo": "admin@example.com", "contrasena": CLAVE},
        headers={"User-Agent": "Pruebas/1.0"},
    )
    fallo, exito = accesos.registros
    assert fallo.resultado == "credenciales_invalidas"
    assert exito.resultado == "exitoso"
    assert exito.usuario_id == admin.id
    assert exito.ip == "testclient"
    assert exito.user_agent == "Pruebas/1.0"


def test_bloqueo_responde_429_con_retry_after(client, admin, accesos):
    for _ in range(MAX_INTENTOS_FALLIDOS):
        assert (
            _login(client, "admin@example.com", "ClaveIncorrecta1").status_code == 401
        )
    r = _login(client, "admin@example.com")
    assert r.status_code == 429
    assert r.headers["retry-after"] == "900"
    assert "intentos" in r.json()["detail"]
    assert accesos.registros[-1].resultado == "bloqueado"


# --- Sesión -------------------------------------------------------------------------


def test_yo_sin_sesion_401(client):
    assert client.get("/api/auth/yo").status_code == 401


def test_yo_con_sesion(client, moderador):
    _login(client, "mod@example.com")
    r = client.get("/api/auth/yo")
    assert r.status_code == 200
    assert r.json()["correo"] == "mod@example.com"
    assert r.json()["permisos"] == sorted(r.json()["permisos"])


def test_logout_borra_la_cookie(client, moderador):
    _login(client, "mod@example.com")
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert f'{NOMBRE_COOKIE}=""' in r.headers["set-cookie"]
    assert client.get("/api/auth/yo").status_code == 401


def test_cookie_alterada_401(client, moderador):
    _login(client, "mod@example.com")
    token = client.cookies[NOMBRE_COOKIE]
    client.cookies.set(NOMBRE_COOKIE, token[:-3] + "abc")
    assert client.get("/api/auth/yo").status_code == 401


def test_cabecera_x_rol_debug_ya_no_autentica(client):
    r = client.get("/api/escenarios", headers={"X-Rol-Debug": "administrador"})
    assert r.status_code == 401
    r = client.get("/api/usuarios", headers={"X-Rol-Debug": "administrador"})
    assert r.status_code == 401


def test_desactivar_cuenta_corta_la_sesion_abierta(client, moderador, usuarios):
    _login(client, "mod@example.com")
    assert client.get("/api/auth/yo").status_code == 200
    moderador.activo = False
    usuarios.guardar(moderador)
    assert client.get("/api/auth/yo").status_code == 401


def test_cambio_de_rol_aplica_sin_volver_a_entrar(client, usuarios):
    a1 = _usuario(usuarios, "a1@example.com", RolNombre.ADMINISTRADOR)
    _usuario(usuarios, "a2@example.com", RolNombre.ADMINISTRADOR)
    _login(client, "a1@example.com")
    assert client.get("/api/usuarios").status_code == 200
    a1.rol = RolNombre.MODERADOR
    usuarios.guardar(a1)
    assert client.get("/api/usuarios").status_code == 403
    assert client.get("/api/auth/yo").json()["rol"] == "moderador"


# --- Historial de accesos ------------------------------------------------------------


def test_historial_solo_para_administrador(client, admin, moderador):
    _login(client, "mod@example.com")
    assert client.get("/api/accesos").status_code == 403


def test_historial_recientes_primero_y_filtros(client, admin, moderador):
    _login(client, "mod@example.com", "ClaveIncorrecta1")
    _login(client, "mod@example.com")
    _login(client, "admin@example.com")
    r = client.get("/api/accesos")
    assert r.status_code == 200
    assert [a["resultado"] for a in r.json()] == [
        "exitoso",
        "exitoso",
        "credenciales_invalidas",
    ]
    assert r.json()[0]["correo"] == "admin@example.com"
    r = client.get("/api/accesos", params={"resultado": "credenciales_invalidas"})
    assert len(r.json()) == 1
    r = client.get("/api/accesos", params={"usuario_id": str(moderador.id)})
    assert len(r.json()) == 2
    r = client.get("/api/accesos", params={"q": "admin"})
    assert len(r.json()) == 1
    assert client.get("/api/accesos", params={"limite": 0}).status_code == 422
