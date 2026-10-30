"""Leaderboard en vivo para observadores (PB-12, RF-02).

Reutiliza el acumulado de PB-10 (`ServicioRegistroRespuestas.acumulado_de`):
nunca carga el texto de las respuestas, las opciones elegidas ni los
criterios de una tarea, así que estructuralmente no puede filtrarse nada de
eso en la salida.

Reglas de acceso:

- Observador y Administrador: cualquier sesión en curso o finalizada.
- Moderador: solo las suyas (otra sesión, o una en borrador o programada,
  es "no encontrada" igual que para cualquiera).
- El permiso `leaderboard:ver` (401/403) lo resuelve el router.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.respuestas import PuntajesSesion, ServicioRegistroRespuestas
from app.application.sesiones import SesionNoEncontrada
from app.domain.evaluacion import Acumulado
from app.domain.sesiones import EstadoSesion, SesionTabletop
from app.ports.en_vivo import AlmacenEnVivo
from app.ports.escenario_repository import CatalogoRepository
from app.ports.respuesta_repository import RespuestaRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import UsuarioRepository

# El leaderboard solo tiene sentido con la sesión en marcha o ya jugada; un
# borrador o una programada todavía no tienen respuestas que mostrar.
VISIBLES_LEADERBOARD = (EstadoSesion.EN_CURSO, EstadoSesion.FINALIZADA)


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class SesionLeaderboard:
    id: UUID
    nombre: str
    estado: EstadoSesion
    total_injects: int
    inject_actual: int
    iniciada_en: datetime | None
    finalizada_en: datetime | None

    @classmethod
    def desde(cls, s: SesionTabletop) -> "SesionLeaderboard":
        return cls(
            id=s.id,
            nombre=s.nombre,
            estado=s.estado,
            total_injects=len(s.injects),
            inject_actual=s.inject_actual,
            iniciada_en=s.iniciada_en,
            finalizada_en=s.finalizada_en,
        )


@dataclass
class PosicionParticipante:
    posicion: int
    usuario_id: UUID
    nombre: str
    rol_codigo: str
    rol_nombre: str
    acumulado: Acumulado


@dataclass
class PosicionRol:
    posicion: int
    rol_codigo: str
    rol_nombre: str
    participantes: int
    acumulado: Acumulado


@dataclass
class RankingLeaderboard:
    sesion: SesionLeaderboard
    actualizado_en: datetime
    participantes: list[PosicionParticipante]
    roles: list[PosicionRol]


def _con_posiciones(items: list, clave_de: Callable) -> list[tuple[int, object]]:
    """Ranking de competencia estándar: los empates comparten posición y la
    siguiente salta (1, 1, 3), ordenado de mayor a menor según `clave_de`
    (una tupla: solo comparten posición quienes empatan en todos sus valores)."""
    ordenados = sorted(items, key=clave_de, reverse=True)
    resultado = []
    posicion = 0
    anterior = None
    for i, item in enumerate(ordenados, start=1):
        clave = clave_de(item)
        if clave != anterior:
            posicion = i
            anterior = clave
        resultado.append((posicion, item))
    return resultado


def _clave_ranking(acumulado: Acumulado) -> tuple[float, float]:
    """Porcentaje primero (desempata tareas con distinto puntaje máximo, p.
    ej. 10 vs 15), puntos absolutos como desempate si el porcentaje coincide."""
    return (acumulado.porcentaje, acumulado.puntaje)


class ServicioLeaderboard:
    def __init__(
        self,
        sesiones: SesionRepository,
        respuestas: RespuestaRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
        almacen: AlmacenEnVivo,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.sesiones = sesiones
        self.reloj = reloj
        self.registro = ServicioRegistroRespuestas(
            sesiones, respuestas, catalogo, usuarios, almacen, reloj
        )

    def sesiones_visibles(
        self, usuario_id: UUID, es_moderador: bool
    ) -> list[SesionLeaderboard]:
        if es_moderador:
            sesiones = [
                s
                for s in self.sesiones.listar_por_moderador(usuario_id)
                if s.estado in VISIBLES_LEADERBOARD
            ]
        else:
            sesiones = self.sesiones.listar_por_estados(VISIBLES_LEADERBOARD)
        return [SesionLeaderboard.desde(s) for s in sesiones]

    def ranking(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> RankingLeaderboard:
        sesion = self._visible(sesion_id, usuario_id, es_moderador)
        puntajes = self.registro.acumulado_de(sesion)
        return RankingLeaderboard(
            sesion=SesionLeaderboard.desde(sesion),
            actualizado_en=self.reloj(),
            participantes=self._ranking_participantes(puntajes),
            roles=self._ranking_roles(puntajes),
        )

    # --- apoyo ----------------------------------------------------------------------

    def _visible(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> SesionTabletop:
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.estado not in VISIBLES_LEADERBOARD:
            raise SesionNoEncontrada(str(sesion_id))
        if es_moderador and sesion.moderador_id != usuario_id:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion

    @staticmethod
    def _ranking_participantes(puntajes: PuntajesSesion) -> list[PosicionParticipante]:
        return [
            PosicionParticipante(
                posicion=posicion,
                usuario_id=p.usuario_id,
                nombre=p.nombre,
                rol_codigo=p.rol_codigo,
                rol_nombre=p.rol_nombre,
                acumulado=p.acumulado,
            )
            for posicion, p in _con_posiciones(
                puntajes.participantes, lambda p: _clave_ranking(p.acumulado)
            )
        ]

    @staticmethod
    def _ranking_roles(puntajes: PuntajesSesion) -> list[PosicionRol]:
        return [
            PosicionRol(
                posicion=posicion,
                rol_codigo=r.rol_codigo,
                rol_nombre=r.rol_nombre,
                participantes=r.participantes,
                acumulado=r.acumulado,
            )
            for posicion, r in _con_posiciones(
                puntajes.roles, lambda r: _clave_ranking(r.acumulado)
            )
        ]
