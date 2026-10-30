"""Monitoreo de sesiones activas para el Administrador (PC-24, RNF).

Solo lectura y de alcance distinto al leaderboard (PB-12): mientras el
leaderboard compara avance de cualquier sesión en curso o finalizada,
monitoreo muestra de un vistazo TODAS las sesiones EN_CURSO (hasta
`maximo_activas` a la vez) para que el Administrador vea si el cupo
configurado está lleno y pueda entrar a cualquiera en modo lectura.

Reutiliza `ServicioRegistroRespuestas.acumulado_de` (PB-10) igual que el
leaderboard: nunca carga texto de respuestas, opciones elegidas ni
criterios de una tarea, así que estructuralmente no puede filtrarse nada
de eso en la salida (mismo principio de mínimo privilegio que PB-12).

`excede_duracion` (PC-24) marca una sesión que lleva más tiempo corrido
que su `duracion_minutos` programada: una señal de que podría estar
abandonada (el moderador nunca la cerró). Por ahora solo se muestra en el
panel; forzar su cierre desde aquí queda fuera de esta historia (ver
docs/monitoreo.md).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.en_vivo import ServicioEnVivo, excede_duracion
from app.application.respuestas import (
    PuntajeParticipante,
    PuntajeRol,
    ServicioRegistroRespuestas,
)
from app.application.sesiones import SesionNoEncontrada
from app.domain.sesiones import (
    MAX_SESIONES_ACTIVAS_POR_DEFECTO,
    EstadoSesion,
    SesionTabletop,
)
from app.ports.en_vivo import AlmacenEnVivo
from app.ports.escenario_repository import CatalogoRepository, EscenarioRepository
from app.ports.respuesta_repository import RespuestaRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import UsuarioRepository


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class FilaMonitoreo:
    """Una sesión EN_CURSO vista desde el panel de monitoreo. Nunca incluye
    texto de respuestas, opciones ni criterios."""

    id: UUID
    nombre: str
    moderador_nombre: str
    escenario_nombre: str
    pausada: bool
    invitados: int
    # Participantes invitados conectados ahora (sin contar al moderador).
    conectados: int
    inject_actual: int
    total_injects: int
    respuestas_recibidas: int
    respuestas_esperadas: int
    porcentaje_avance: float
    segundos_transcurridos: int
    iniciada_en: datetime | None
    duracion_minutos: int | None
    excede_duracion: bool


@dataclass
class ResumenMonitoreo:
    activas: int
    maximo: int
    sesiones: list[FilaMonitoreo]


@dataclass
class DetalleMonitoreo:
    sesion: FilaMonitoreo
    participantes: list[PuntajeParticipante]
    roles: list[PuntajeRol]
    # Quién está conectado ahora mismo (no solo el conteo de FilaMonitoreo):
    # para que la vista de lectura marque el mismo punto verde/gris que ve
    # el moderador en ProgresoParticipantes/AvancePorRol (PB-11).
    conectados_ids: frozenset[UUID]


class ServicioMonitoreo:
    def __init__(
        self,
        sesiones: SesionRepository,
        respuestas: RespuestaRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
        escenarios: EscenarioRepository,
        almacen: AlmacenEnVivo,
        maximo_activas: int = MAX_SESIONES_ACTIVAS_POR_DEFECTO,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.sesiones = sesiones
        self.escenarios = escenarios
        self.usuarios = usuarios
        self.maximo_activas = maximo_activas
        self.reloj = reloj
        self.en_vivo = ServicioEnVivo(sesiones, almacen, reloj, maximo_activas)
        self.registro = ServicioRegistroRespuestas(
            sesiones, respuestas, catalogo, usuarios, almacen, reloj
        )

    def resumen(self) -> ResumenMonitoreo:
        """Cupo actual (RF-, RNF) y una fila por cada sesión EN_CURSO."""
        activas = self.sesiones.listar_por_estados((EstadoSesion.EN_CURSO,))
        filas = [self._fila(s) for s in activas]
        return ResumenMonitoreo(
            activas=len(filas), maximo=self.maximo_activas, sesiones=filas
        )

    def detalle(self, sesion_id: UUID) -> DetalleMonitoreo:
        """Vista de lectura de una sesión, con avance por participante y rol.

        404 si la sesión no existe o no está EN_CURSO: el monitoreo solo
        tiene sentido mientras la sesión corre.
        """
        sesion = self._activa(sesion_id)
        puntajes = self.registro.acumulado_de(sesion)
        return DetalleMonitoreo(
            sesion=self._fila(sesion),
            participantes=puntajes.participantes,
            roles=puntajes.roles,
            conectados_ids=self.en_vivo.vista(sesion).conectados,
        )

    # --- apoyo ----------------------------------------------------------------------

    def _activa(self, sesion_id: UUID) -> SesionTabletop:
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.estado != EstadoSesion.EN_CURSO:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion

    def _fila(self, sesion: SesionTabletop) -> FilaMonitoreo:
        vista = self.en_vivo.vista(sesion)
        moderador = self.usuarios.obtener_por_id(sesion.moderador_id)
        escenario = self.escenarios.obtener(sesion.escenario_id)
        puntajes = self.registro.acumulado_de(sesion)
        recibidas = sum(p.acumulado.respondidas for p in puntajes.participantes)
        esperadas = recibidas + sum(
            p.acumulado.sin_responder for p in puntajes.participantes
        )
        # Solo los invitados: la conexión del moderador también está en
        # `vista.conectados` y no debe contar como participante (no "6/5").
        invitados = {p.usuario_id for p in sesion.participantes}
        return FilaMonitoreo(
            id=sesion.id,
            nombre=sesion.nombre,
            moderador_nombre=moderador.nombre if moderador else "—",
            escenario_nombre=escenario.nombre if escenario else "—",
            pausada=vista.pausada,
            invitados=len(invitados),
            conectados=len(vista.conectados & invitados),
            inject_actual=vista.inject_actual,
            total_injects=vista.total_injects,
            respuestas_recibidas=recibidas,
            respuestas_esperadas=esperadas,
            porcentaje_avance=round(100 * recibidas / esperadas, 1)
            if esperadas
            else 0.0,
            segundos_transcurridos=vista.segundos_transcurridos,
            iniciada_en=vista.iniciada_en,
            duracion_minutos=vista.duracion_minutos,
            excede_duracion=excede_duracion(sesion, self.reloj()),
        )
