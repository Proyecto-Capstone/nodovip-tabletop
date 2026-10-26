"""Invitaciones por correo y acceso del participante (PB-06). Sin base de datos."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.invitaciones import (
    ServicioInvitaciones,
    formato_fecha,
    mensaje_invitacion,
)
from app.application.sesiones import ServicioSesiones, SesionNoEncontrada
from app.domain.escenarios import (
    Escenario,
    EstadoEscenario,
    Inject,
    Nivel,
    RolEjercicio,
    Tarea,
)
from app.domain.sesiones import (
    EstadoInvitacion,
    ParticipanteSesion,
    ReglaSesionError,
    SesionTabletop,
)
from app.domain.usuarios import RolNombre, Usuario
from tests.fakes import (
    EnviadorFalso,
    RelojFalso,
    RepoSesionesEnMemoria,
    RepoUsuariosEnMemoria,
)

AHORA = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)


class RepoEscenarios:
    def __init__(self, escenario):
        self.escenario = escenario

    def obtener(self, escenario_id):
        return self.escenario if escenario_id == self.escenario.id else None


class Catalogo:
    def roles_ejercicio(self):
        return [RolEjercicio("ti", "Responsable de TI"), RolEjercicio("legal", "Legal")]


def _usuario(nombre, rol=RolNombre.PARTICIPANTE, activo=True):
    return Usuario(
        correo=f"{nombre.lower()}@prueba.test",
        nombre=nombre,
        password_hash="x",
        rol=rol,
        activo=activo,
    )


@pytest.fixture
def e():
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
    gente = {
        n: usuarios.guardar(_usuario(n, r))
        for n, r in [
            ("Mónica", RolNombre.MODERADOR),
            ("Ana", RolNombre.PARTICIPANTE),
            ("Luis", RolNombre.PARTICIPANTE),
            ("Eva", RolNombre.PARTICIPANTE),
        ]
    }
    repo = RepoSesionesEnMemoria()
    enviador = EnviadorFalso()
    reloj = RelojFalso(AHORA)
    invitaciones = ServicioInvitaciones(
        repo,
        Catalogo(),
        usuarios,
        enviador,
        "https://tabletop.nodovip.test/",
        reloj=reloj,
        escenarios=RepoEscenarios(escenario),
    )
    sesiones = ServicioSesiones(
        repo,
        RepoEscenarios(escenario),
        Catalogo(),
        usuarios,
        reloj=reloj,
        invitar=invitaciones.enviar_pendientes,
    )
    sesion = sesiones.crear(escenario.id, gente["Mónica"].id, "Simulacro Q4")
    sesion.participantes = [
        ParticipanteSesion(gente["Ana"].id, "ti"),
        ParticipanteSesion(gente["Luis"].id, "legal"),
    ]
    sesion.fecha_programada = AHORA + timedelta(days=2)
    sesion.duracion_minutos = 90
    sesiones.actualizar(sesion.id, gente["Mónica"].id, sesion)
    return {
        "sesiones": sesiones,
        "invitaciones": invitaciones,
        "repo": repo,
        "usuarios": usuarios,
        "enviador": enviador,
        "reloj": reloj,
        "sesion_id": sesion.id,
        **gente,
    }


def _programar(e) -> SesionTabletop:
    return e["sesiones"].programar(e["sesion_id"], e["Mónica"].id)


def _invitacion(sesion, usuario) -> ParticipanteSesion:
    p = sesion.participante_de(usuario.id)
    assert p is not None
    return p


# --- Envío al programar -------------------------------------------------------------


def test_programar_envia_una_invitacion_a_cada_participante(e):
    sesion = _programar(e)

    assert len(e["enviador"].enviados) == 2
    correo = e["enviador"].para("ana@prueba.test")[0]
    assert correo.asunto == "Invitación al ejercicio tabletop: Simulacro Q4"
    assert "Mónica te invitó" in correo.texto
    assert "con el rol de Responsable de TI" in correo.texto
    assert f"https://tabletop.nodovip.test/mis-sesiones/{sesion.id}" in correo.texto
    ana = _invitacion(sesion, e["Ana"])
    assert ana.invitacion == EstadoInvitacion.ENVIADA
    assert ana.invitacion_enviada_en == AHORA


def test_un_fallo_de_brevo_no_detiene_a_los_demas_y_se_registra(e):
    e["enviador"].fallar_para = {"luis@prueba.test"}
    sesion = _programar(e)

    assert _invitacion(sesion, e["Ana"]).invitacion == EstadoInvitacion.ENVIADA
    luis = _invitacion(sesion, e["Luis"])
    assert luis.invitacion == EstadoInvitacion.FALLIDA
    assert "invalid email" in luis.invitacion_error
    # Queda guardado: el moderador lo ve en el paso 6.
    guardada = e["repo"].obtener(sesion.id)
    assert _invitacion(guardada, e["Luis"]).invitacion == EstadoInvitacion.FALLIDA


def test_reenviar_solo_manda_las_pendientes_o_fallidas(e):
    e["enviador"].fallar_para = {"luis@prueba.test"}
    _programar(e)
    e["enviador"].fallar_para = set()

    sesion = e["sesiones"].enviar_invitaciones(e["sesion_id"], e["Mónica"].id)

    assert len(e["enviador"].para("ana@prueba.test")) == 1
    assert len(e["enviador"].para("luis@prueba.test")) == 1
    luis = _invitacion(sesion, e["Luis"])
    assert luis.invitacion == EstadoInvitacion.ENVIADA
    assert luis.invitacion_error is None


def test_no_se_envian_invitaciones_de_un_borrador(e):
    with pytest.raises(ReglaSesionError):
        e["sesiones"].enviar_invitaciones(e["sesion_id"], e["Mónica"].id)
    assert e["enviador"].enviados == []


def test_cuenta_desactivada_queda_como_fallida(e):
    ana = e["Ana"]
    ana.activo = False
    e["usuarios"].guardar(ana)
    sesion = e["repo"].obtener(e["sesion_id"])
    sesion.programar(AHORA)
    sesion = e["invitaciones"].enviar_pendientes(sesion)

    assert _invitacion(sesion, ana).invitacion == EstadoInvitacion.FALLIDA
    assert e["enviador"].para("ana@prueba.test") == []


def test_editar_una_sesion_programada_conserva_las_invitaciones(e):
    sesion = _programar(e)
    # Luis deja Legal y entra Eva: Ana conserva "enviada", Eva queda pendiente.
    sesion.participantes = [
        ParticipanteSesion(e["Ana"].id, "ti"),
        ParticipanteSesion(e["Eva"].id, "legal"),
    ]
    sesion = e["sesiones"].actualizar(sesion.id, e["Mónica"].id, sesion)

    assert _invitacion(sesion, e["Ana"]).invitacion == EstadoInvitacion.ENVIADA
    assert _invitacion(sesion, e["Eva"]).invitacion == EstadoInvitacion.PENDIENTE
    sesion = e["sesiones"].enviar_invitaciones(sesion.id, e["Mónica"].id)
    assert _invitacion(sesion, e["Eva"]).invitacion == EstadoInvitacion.ENVIADA
    assert len(e["enviador"].para("ana@prueba.test")) == 1


# --- Vista del participante ------------------------------------------------------------


def test_el_participante_ve_su_sesion_y_su_rol(e):
    _programar(e)
    [vista] = e["invitaciones"].mis_sesiones(e["Luis"].id)

    assert vista.sesion.nombre == "Simulacro Q4"
    assert vista.rol_nombre == "Legal"
    assert vista.moderador_nombre == "Mónica"
    assert vista.escenario_nombre == "Ransomware en sucursal"


def test_un_borrador_no_aparece_para_el_participante(e):
    assert e["invitaciones"].mis_sesiones(e["Ana"].id) == []
    with pytest.raises(SesionNoEncontrada):
        e["invitaciones"].obtener(e["sesion_id"], e["Ana"].id)


def test_no_puede_ver_una_sesion_a_la_que_no_fue_invitado(e):
    _programar(e)
    with pytest.raises(SesionNoEncontrada):
        e["invitaciones"].obtener(e["sesion_id"], e["Eva"].id)
    with pytest.raises(SesionNoEncontrada):
        e["invitaciones"].aceptar(e["sesion_id"], e["Eva"].id)
    assert e["invitaciones"].mis_sesiones(e["Eva"].id) == []


def test_aceptar_registra_la_fecha_y_es_idempotente(e):
    _programar(e)
    vista = e["invitaciones"].aceptar(e["sesion_id"], e["Ana"].id)
    assert vista.participante.invitacion == EstadoInvitacion.ACEPTADA
    assert vista.participante.invitacion_aceptada_en == AHORA

    e["reloj"].avanzar(hours=1)
    vista = e["invitaciones"].aceptar(e["sesion_id"], e["Ana"].id)
    assert vista.participante.invitacion_aceptada_en == AHORA
    # Un reenvío no la devuelve a "enviada".
    sesion = e["sesiones"].enviar_invitaciones(e["sesion_id"], e["Mónica"].id)
    assert _invitacion(sesion, e["Ana"]).invitacion == EstadoInvitacion.ACEPTADA


# --- Contenido del correo ---------------------------------------------------------------


def test_formato_fecha_en_hora_de_ecuador():
    fecha = datetime(2026, 10, 27, 14, 0, tzinfo=UTC)
    assert formato_fecha(fecha) == "27 de octubre de 2026, 09:00 (hora de Ecuador)"


def test_el_html_del_correo_escapa_los_datos():
    sesion = SesionTabletop.__new__(SesionTabletop)
    sesion.id = uuid4()
    sesion.nombre = "<script>alert(1)</script>"
    sesion.fecha_programada = None
    sesion.duracion_minutos = None
    usuario = _usuario("Ana <b>")

    m = mensaje_invitacion(sesion, usuario, "Legal", "Mónica", "https://x.test/s")

    assert "<script>" not in m.html
    assert "&lt;script&gt;" in m.html
    assert "Ana &lt;b&gt;" in m.html
