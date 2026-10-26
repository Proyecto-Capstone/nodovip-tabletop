"""Casos de uso de invitaciones y acceso del participante (PB-06, RF-01, RF-05).

- El moderador envía (o reenvía) las invitaciones de una sesión programada.
- El participante ve solo las sesiones a las que fue invitado y acepta la suya.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from html import escape
from uuid import UUID

from app.application.sesiones import SesionNoEncontrada
from app.domain.sesiones import ParticipanteSesion, SesionTabletop
from app.domain.usuarios import Usuario
from app.ports.correo import EnviadorCorreos, ErrorEnvioCorreo, MensajeCorreo
from app.ports.escenario_repository import CatalogoRepository, EscenarioRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import UsuarioRepository

# Ecuador no tiene horario de verano: UTC-5 fijo, sin depender de tzdata.
HORA_ECUADOR = timezone(timedelta(hours=-5))
MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class SesionDelParticipante:
    """Lo que ve el participante: su sesión y su rol, sin tareas ni respuestas."""

    sesion: SesionTabletop
    participante: ParticipanteSesion
    moderador_nombre: str
    rol_nombre: str
    escenario_nombre: str
    escenario_descripcion: str


def formato_fecha(fecha: datetime | None) -> str:
    if fecha is None:
        return "por definir"
    f = fecha.astimezone(HORA_ECUADOR)
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}, {f:%H:%M} (hora de Ecuador)"


def mensaje_invitacion(
    sesion: SesionTabletop,
    usuario: Usuario,
    rol_nombre: str,
    moderador_nombre: str,
    enlace: str,
) -> MensajeCorreo:
    fecha = formato_fecha(sesion.fecha_programada)
    duracion = f"{sesion.duracion_minutos} minutos" if sesion.duracion_minutos else ""
    texto = (
        f"Hola {usuario.nombre}:\n\n"
        f"{moderador_nombre} te invitó al ejercicio tabletop «{sesion.nombre}» "
        f"con el rol de {rol_nombre}.\n\n"
        f"Fecha: {fecha}\n"
        + (f"Duración: {duracion}\n" if duracion else "")
        + f"\nIngresa con tu cuenta de NODOVIP para confirmar tu asistencia:\n{enlace}\n\n"
        "Este es un ejercicio de simulación con datos ficticios.\n"
    )
    # Todo dato que viene de usuarios se escapa antes de ir al HTML.
    e = {
        "nombre": escape(usuario.nombre),
        "moderador": escape(moderador_nombre),
        "sesion": escape(sesion.nombre),
        "rol": escape(rol_nombre),
        "fecha": escape(fecha),
        "duracion": escape(duracion),
        "enlace": escape(enlace, quote=True),
    }
    html = f"""<!doctype html>
<html lang="es"><body style="font-family:Arial,sans-serif;color:#1c1e2e;background:#eef0f4;padding:24px">
<div style="max-width:560px;margin:auto;background:#fff;border-radius:10px;padding:24px">
<p style="margin:0 0 16px;font-weight:bold;color:#1c1d33">NODOVIP — Tabletop Exercise</p>
<p>Hola {e["nombre"]}:</p>
<p>{e["moderador"]} te invitó al ejercicio tabletop <strong>{e["sesion"]}</strong>
con el rol de <strong>{e["rol"]}</strong>.</p>
<ul>
<li><strong>Fecha:</strong> {e["fecha"]}</li>
{f"<li><strong>Duración:</strong> {e["duracion"]}</li>" if duracion else ""}
</ul>
<p><a href="{e["enlace"]}" style="display:inline-block;background:#1c1d33;color:#fff;
padding:10px 18px;border-radius:8px;text-decoration:none">Ver mi sesión y confirmar</a></p>
<p style="font-size:12px;color:#6b7085">Si el botón no funciona, copia este enlace:
{e["enlace"]}<br>Este es un ejercicio de simulación con datos ficticios.</p>
</div></body></html>"""
    return MensajeCorreo(
        destinatario_correo=usuario.correo,
        destinatario_nombre=usuario.nombre,
        asunto=f"Invitación al ejercicio tabletop: {sesion.nombre}",
        html=html,
        texto=texto,
    )


class ServicioInvitaciones:
    def __init__(
        self,
        repo: SesionRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
        enviador: EnviadorCorreos,
        url_aplicacion: str,
        reloj: Callable[[], datetime] = _ahora,
        escenarios: EscenarioRepository | None = None,
    ):
        self.repo = repo
        self.escenarios = escenarios
        self.catalogo = catalogo
        self.usuarios = usuarios
        self.enviador = enviador
        self.url_aplicacion = url_aplicacion.rstrip("/")
        self.reloj = reloj

    # --- Moderador --------------------------------------------------------------

    def enviar_pendientes(self, sesion: SesionTabletop) -> SesionTabletop:
        """Envía las invitaciones pendientes o fallidas y guarda el resultado.

        Un fallo de Brevo no detiene a los demás: queda registrado en la
        invitación para reenviarla después desde el paso 6.
        """
        roles = {r.codigo: r.nombre for r in self.catalogo.roles_ejercicio()}
        moderador = self.usuarios.obtener_por_id(sesion.moderador_id)
        nombre_moderador = moderador.nombre if moderador else "El moderador"
        enlace = f"{self.url_aplicacion}/mis-sesiones/{sesion.id}"
        for p in sesion.invitaciones_por_enviar():
            usuario = self.usuarios.obtener_por_id(p.usuario_id)
            if usuario is None or not usuario.activo:
                p.marcar_fallida("La cuenta del participante no está activa")
                continue
            mensaje = mensaje_invitacion(
                sesion,
                usuario,
                roles.get(p.rol_codigo, p.rol_codigo),
                nombre_moderador,
                enlace,
            )
            try:
                self.enviador.enviar(mensaje)
                p.marcar_enviada(self.reloj())
            except ErrorEnvioCorreo as e:
                p.marcar_fallida(str(e))
        return self.repo.guardar(sesion)

    # --- Participante -----------------------------------------------------------

    def mis_sesiones(self, usuario_id: UUID) -> list[SesionDelParticipante]:
        sesiones = [
            s
            for s in self.repo.listar_por_participante(usuario_id)
            if s.visible_para(usuario_id)
        ]
        sesiones.sort(
            key=lambda s: s.fecha_programada or datetime.max.replace(tzinfo=UTC)
        )
        return [self._vista(s, usuario_id) for s in sesiones]

    def obtener(self, sesion_id: UUID, usuario_id: UUID) -> SesionDelParticipante:
        """404 si no fue invitado: no se revela que la sesión existe."""
        sesion = self.repo.obtener(sesion_id)
        if sesion is None or not sesion.visible_para(usuario_id):
            raise SesionNoEncontrada(str(sesion_id))
        return self._vista(sesion, usuario_id)

    def aceptar(self, sesion_id: UUID, usuario_id: UUID) -> SesionDelParticipante:
        sesion = self.repo.obtener(sesion_id)
        if sesion is None or not sesion.visible_para(usuario_id):
            raise SesionNoEncontrada(str(sesion_id))
        sesion.aceptar_invitacion(usuario_id, self.reloj())
        return self._vista(self.repo.guardar(sesion), usuario_id)

    def _vista(self, sesion: SesionTabletop, usuario_id: UUID) -> SesionDelParticipante:
        moderador = self.usuarios.obtener_por_id(sesion.moderador_id)
        participante = sesion.participante_de(usuario_id)
        assert participante is not None
        roles = {r.codigo: r.nombre for r in self.catalogo.roles_ejercicio()}
        escenario = (
            self.escenarios.obtener(sesion.escenario_id) if self.escenarios else None
        )
        return SesionDelParticipante(
            sesion=sesion,
            participante=participante,
            moderador_nombre=moderador.nombre if moderador else "Moderador",
            rol_nombre=roles.get(participante.rol_codigo, participante.rol_codigo),
            escenario_nombre=escenario.nombre if escenario else "",
            escenario_descripcion=escenario.descripcion if escenario else "",
        )
