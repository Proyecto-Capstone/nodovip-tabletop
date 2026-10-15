"""Reglas de autenticación (PB-01): dominio y caso de uso con dobles en memoria."""

from uuid import UUID

import pytest

from app.application.autenticacion import (
    AccesoBloqueado,
    CredencialesInvalidas,
    ServicioAutenticacion,
)
from app.domain.autenticacion import (
    MAX_INTENTOS_FALLIDOS,
    ResultadoAcceso,
    fallos_consecutivos,
)
from app.domain.usuarios import RolNombre, Usuario
from tests.fakes import (
    HasherFalso,
    RelojFalso,
    RepoAccesosEnMemoria,
    RepoUsuariosEnMemoria,
)

CLAVE = "Nodovip2026seguro"
IP = "10.0.0.7"
R = ResultadoAcceso


class TokensFalsos:
    def emitir(self, usuario_id):
        return f"token::{usuario_id}"

    def validar(self, token):
        try:
            return UUID(token.removeprefix("token::"))
        except ValueError:
            return None


@pytest.fixture
def reloj():
    return RelojFalso()


@pytest.fixture
def entorno(reloj):
    usuarios = RepoUsuariosEnMemoria()
    accesos = RepoAccesosEnMemoria()
    hasher = HasherFalso()
    servicio = ServicioAutenticacion(
        usuarios, accesos, hasher, TokensFalsos(), reloj=reloj
    )
    ana = usuarios.guardar(
        Usuario(
            correo="ana@example.com",
            nombre="Ana Pérez",
            password_hash=hasher.hashear(CLAVE),
            rol=RolNombre.MODERADOR,
        )
    )
    return servicio, usuarios, accesos, hasher, ana


def _fallar(servicio, veces, correo="ana@example.com"):
    for _ in range(veces):
        with pytest.raises(CredencialesInvalidas):
            servicio.iniciar_sesion(correo, "ClaveIncorrecta1", ip=IP)


# --- Dominio --------------------------------------------------------------------


def test_fallos_consecutivos_se_cortan_en_el_ultimo_exito():
    assert fallos_consecutivos([]) == 0
    assert fallos_consecutivos([R.CREDENCIALES_INVALIDAS] * 3) == 3
    resultados = [R.CREDENCIALES_INVALIDAS, R.EXITOSO, R.CREDENCIALES_INVALIDAS]
    assert fallos_consecutivos(resultados) == 1


def test_inactivo_cuenta_como_fallo_y_bloqueado_no():
    resultados = [R.BLOQUEADO, R.USUARIO_INACTIVO, R.BLOQUEADO]
    assert fallos_consecutivos(resultados) == 1


# --- Iniciar sesión ---------------------------------------------------------------


def test_login_correcto_emite_token_y_registra_el_acceso(entorno):
    servicio, _, accesos, _, ana = entorno
    sesion = servicio.iniciar_sesion(
        "  ANA@example.com ", CLAVE, ip=IP, user_agent="Firefox"
    )
    assert sesion.usuario.id == ana.id
    assert sesion.token == f"token::{ana.id}"
    [registro] = accesos.registros
    assert registro.resultado == R.EXITOSO
    assert registro.correo == "ana@example.com"
    assert registro.usuario_id == ana.id
    assert registro.ip == IP
    assert registro.user_agent == "Firefox"
    assert registro.fecha_hora is not None


def test_clave_incorrecta_registra_el_fallo_con_el_usuario(entorno):
    servicio, _, accesos, _, ana = entorno
    _fallar(servicio, 1)
    [registro] = accesos.registros
    assert registro.resultado == R.CREDENCIALES_INVALIDAS
    assert registro.usuario_id == ana.id


def test_correo_inexistente_verifica_igual_contra_el_relleno(entorno):
    servicio, _, accesos, hasher, _ = entorno
    _fallar(servicio, 1, correo="nadie@example.com")
    # Se ejecutó la verificación aunque el usuario no exista (mismo tiempo).
    assert hasher.verificaciones == 1
    [registro] = accesos.registros
    assert registro.usuario_id is None
    assert registro.correo == "nadie@example.com"


def test_usuario_inactivo_no_entra_y_queda_registrado(entorno):
    servicio, usuarios, accesos, _, ana = entorno
    ana.activo = False
    usuarios.guardar(ana)
    with pytest.raises(CredencialesInvalidas):
        servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)
    assert accesos.registros[-1].resultado == R.USUARIO_INACTIVO


def test_user_agent_largo_se_recorta(entorno):
    servicio, _, accesos, _, _ = entorno
    servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP, user_agent="x" * 500)
    assert len(accesos.registros[0].user_agent) == 255


# --- Bloqueo por fuerza bruta -------------------------------------------------------


def test_bloquea_tras_cinco_fallos_aunque_la_clave_sea_correcta(entorno):
    servicio, _, accesos, _, _ = entorno
    _fallar(servicio, MAX_INTENTOS_FALLIDOS)
    with pytest.raises(AccesoBloqueado):
        servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)
    assert accesos.registros[-1].resultado == R.BLOQUEADO


def test_cuatro_fallos_no_bloquean(entorno):
    servicio, _, _, _, _ = entorno
    _fallar(servicio, MAX_INTENTOS_FALLIDOS - 1)
    assert servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)


def test_un_acceso_exitoso_reinicia_el_conteo(entorno):
    servicio, _, _, _, _ = entorno
    _fallar(servicio, 4)
    servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)
    _fallar(servicio, 4)
    assert servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)


def test_el_bloqueo_se_levanta_a_los_15_minutos(entorno, reloj):
    servicio, _, _, _, _ = entorno
    _fallar(servicio, MAX_INTENTOS_FALLIDOS)
    reloj.avanzar(minutes=14)
    with pytest.raises(AccesoBloqueado):
        servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)
    reloj.avanzar(minutes=1, seconds=1)
    assert servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)


def test_seguir_intentando_durante_el_bloqueo_no_lo_levanta_antes(entorno, reloj):
    servicio, _, _, _, _ = entorno
    _fallar(servicio, MAX_INTENTOS_FALLIDOS)
    for _ in range(30):
        reloj.avanzar(seconds=10)
        with pytest.raises(AccesoBloqueado):
            servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)


def test_el_bloqueo_es_por_correo(entorno):
    servicio, _, _, _, _ = entorno
    _fallar(servicio, MAX_INTENTOS_FALLIDOS, correo="otro@example.com")
    assert servicio.iniciar_sesion("ana@example.com", CLAVE, ip=IP)


# --- Usuario desde el token ---------------------------------------------------------


def test_usuario_desde_token(entorno):
    servicio, usuarios, _, _, ana = entorno
    assert servicio.usuario_desde_token(f"token::{ana.id}").id == ana.id
    assert servicio.usuario_desde_token("token::basura") is None
    ana.activo = False
    usuarios.guardar(ana)
    assert servicio.usuario_desde_token(f"token::{ana.id}") is None
    usuarios.eliminar(ana.id)
    assert servicio.usuario_desde_token(f"token::{ana.id}") is None
