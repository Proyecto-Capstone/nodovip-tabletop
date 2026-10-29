"""Casos de uso del motor en tiempo real (PB-07, RF-02).

Comandos del moderador: iniciar, lanzar el siguiente inject, pausar, reanudar y
cerrar. Cada comando actualiza el estado en vivo (Redis), lo refleja en
PostgreSQL cuando corresponde y publica un evento para los WebSocket.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.sesiones import SesionNoEncontrada
from app.domain.en_vivo import EstadoEnVivo, EventoEnVivo
from app.domain.escenarios import Inject
from app.domain.sesiones import EstadoSesion, ReglaSesionError, SesionTabletop
from app.ports.en_vivo import AlmacenEnVivo
from app.ports.sesion_repository import SesionRepository


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class VistaEnVivo:
    """Lo que ve cada conexión. El participante recibe la misma vista, salvo
    la lista de quiénes están conectados (solo el número)."""

    sesion_id: UUID
    nombre: str
    estado: EstadoSesion
    total_injects: int
    inject_actual: int
    inject: Inject | None
    pausada: bool
    iniciada_en: datetime | None
    inject_lanzado_en: datetime | None
    segundos_transcurridos: int
    duracion_minutos: int | None
    version: int
    conectados: frozenset[UUID]


def componer_vista(
    sesion: SesionTabletop,
    estado: EstadoEnVivo | None,
    conectados: frozenset[UUID],
    ahora: datetime,
) -> VistaEnVivo:
    """Une los datos fijos de la sesión con su estado en vivo (si lo tiene)."""
    if estado is None:
        estado_sesion = sesion.estado
    elif estado.cerrada:
        estado_sesion = EstadoSesion.FINALIZADA
    else:
        estado_sesion = EstadoSesion.EN_CURSO
    inject_actual = estado.inject_actual if estado else sesion.inject_actual
    inject = next((i for i in sesion.injects if i.orden == inject_actual), None)
    return VistaEnVivo(
        sesion_id=sesion.id,
        nombre=sesion.nombre,
        estado=estado_sesion,
        total_injects=len(sesion.injects),
        inject_actual=inject_actual,
        inject=inject,
        pausada=estado.pausada if estado else False,
        iniciada_en=estado.iniciada_en if estado else sesion.iniciada_en,
        inject_lanzado_en=estado.inject_lanzado_en if estado else None,
        segundos_transcurridos=estado.segundos_transcurridos(ahora) if estado else 0,
        duracion_minutos=sesion.duracion_minutos,
        version=estado.version if estado else 0,
        conectados=conectados,
    )


class ServicioEnVivo:
    def __init__(
        self,
        sesiones: SesionRepository,
        almacen: AlmacenEnVivo,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.sesiones = sesiones
        self.almacen = almacen
        self.reloj = reloj

    # --- Comandos del moderador ---------------------------------------------------

    def iniciar(self, sesion_id: UUID, moderador_id: UUID) -> VistaEnVivo:
        sesion = self._de_moderador(sesion_id, moderador_id)
        ahora = self.reloj()
        sesion.iniciar(ahora)
        estado = EstadoEnVivo(
            sesion.id, total_injects=len(sesion.injects), iniciada_en=ahora
        )
        self.sesiones.guardar(sesion)
        return self._aplicar(sesion, estado)

    def lanzar_inject(self, sesion_id: UUID, moderador_id: UUID) -> VistaEnVivo:
        sesion, estado = self._en_curso(sesion_id, moderador_id)
        estado.lanzar_siguiente_inject(self.reloj())
        # Se refleja en PostgreSQL para poder reconstruir si Redis se pierde.
        sesion.inject_actual = estado.inject_actual
        self.sesiones.guardar(sesion)
        return self._aplicar(sesion, estado)

    def pausar(self, sesion_id: UUID, moderador_id: UUID) -> VistaEnVivo:
        sesion, estado = self._en_curso(sesion_id, moderador_id)
        estado.pausar(self.reloj())
        return self._aplicar(sesion, estado)

    def reanudar(self, sesion_id: UUID, moderador_id: UUID) -> VistaEnVivo:
        sesion, estado = self._en_curso(sesion_id, moderador_id)
        estado.reanudar(self.reloj())
        return self._aplicar(sesion, estado)

    def cerrar(self, sesion_id: UUID, moderador_id: UUID) -> VistaEnVivo:
        """Termina la sesión y la persiste en PostgreSQL (RF-02)."""
        sesion, estado = self._en_curso(sesion_id, moderador_id)
        ahora = self.reloj()
        estado.cerrar(ahora)
        sesion.finalizar(ahora, estado.inject_actual)
        self.sesiones.guardar(sesion)
        vista = self._aplicar(sesion, estado)
        self.almacen.eliminar(sesion.id)
        return vista

    # --- Lectura y conexiones -----------------------------------------------------

    def sesion_para(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> SesionTabletop:
        """La sesión, si el usuario puede seguirla en vivo; si no, 404."""
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None:
            raise SesionNoEncontrada(str(sesion_id))
        if es_moderador and sesion.moderador_id == usuario_id:
            return sesion
        if not es_moderador and sesion.visible_para(usuario_id):
            return sesion
        raise SesionNoEncontrada(str(sesion_id))

    def vista(self, sesion: SesionTabletop) -> VistaEnVivo:
        estado = self._estado(sesion)
        return componer_vista(
            sesion, estado, self.almacen.conectados(sesion.id), self.reloj()
        )

    def conectar(self, sesion_id: UUID, usuario_id: UUID) -> None:
        self.almacen.conectar(sesion_id, usuario_id)
        self._avisar_presencia(sesion_id)

    def desconectar(self, sesion_id: UUID, usuario_id: UUID) -> None:
        self.almacen.desconectar(sesion_id, usuario_id)
        self._avisar_presencia(sesion_id)

    # --- apoyo ----------------------------------------------------------------------

    def _de_moderador(self, sesion_id: UUID, moderador_id: UUID) -> SesionTabletop:
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.moderador_id != moderador_id:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion

    def _en_curso(
        self, sesion_id: UUID, moderador_id: UUID
    ) -> tuple[SesionTabletop, EstadoEnVivo]:
        sesion = self._de_moderador(sesion_id, moderador_id)
        estado = self._estado(sesion)
        if estado is None:
            raise ReglaSesionError(["La sesión no está en curso"])
        return sesion, estado

    def _estado(self, sesion: SesionTabletop) -> EstadoEnVivo | None:
        """Estado en Redis o, si se perdió, reconstruido desde PostgreSQL."""
        if sesion.estado != EstadoSesion.EN_CURSO:
            return None
        estado = self.almacen.obtener(sesion.id)
        if estado is None:
            estado = EstadoEnVivo(
                sesion.id,
                total_injects=len(sesion.injects),
                iniciada_en=sesion.iniciada_en or self.reloj(),
                inject_actual=sesion.inject_actual,
            )
            self.almacen.guardar(estado)
        return estado

    def _aplicar(self, sesion: SesionTabletop, estado: EstadoEnVivo) -> VistaEnVivo:
        self.almacen.guardar(estado)
        conectados = self.almacen.conectados(sesion.id)
        self.almacen.publicar(
            EventoEnVivo(sesion.id, "estado", estado=estado, conectados=conectados)
        )
        return componer_vista(sesion, estado, conectados, self.reloj())

    def _avisar_presencia(self, sesion_id: UUID) -> None:
        self.almacen.publicar(
            EventoEnVivo(
                sesion_id, "presencia", conectados=self.almacen.conectados(sesion_id)
            )
        )
