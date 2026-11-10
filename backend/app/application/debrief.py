"""Debrief de la sesión y resumen personal del participante (PC-45).

Debrief:
- Solo de sesiones **finalizadas** (antes es "no encontrada").
- Lo edita únicamente el moderador dueño de la sesión. Analista y
  Administrador (permiso `reportes:ver`) lo consultan.
- Completarlo lo fija y lo lleva al reporte de brechas; se puede reabrir.

Resumen del participante: al finalizar la sesión, cada participante ve su
puntaje, su posición, cada tarea de su rol con lo que respondió, la
retroalimentación de la evaluación (criterios cumplidos y faltantes, opciones
correctas) y el motivo de los ajustes del moderador. También las lecciones del
debrief si ya se completó.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.respuestas import ServicioRegistroRespuestas
from app.application.sesiones import SesionNoEncontrada
from app.domain.debrief import AccionMejora, Debrief
from app.domain.sesiones import EstadoSesion, SesionTabletop, TipoTarea
from app.ports.debrief import DebriefRepository
from app.ports.en_vivo import AlmacenEnVivo
from app.ports.escenario_repository import CatalogoRepository
from app.ports.respuesta_repository import RespuestaRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import UsuarioRepository


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class VistaDebrief:
    """El debrief (o None si todavía no se empezó) con el contexto de la sesión."""

    sesion: SesionTabletop
    debrief: Debrief | None
    puede_editar: bool
    roles: dict[str, str]


class ServicioDebrief:
    def __init__(
        self,
        sesiones: SesionRepository,
        debriefs: DebriefRepository,
        catalogo: CatalogoRepository,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.sesiones = sesiones
        self.debriefs = debriefs
        self.catalogo = catalogo
        self.reloj = reloj

    def ver(
        self, sesion_id: UUID, usuario_id: UUID, es_moderador: bool
    ) -> VistaDebrief:
        sesion = self._finalizada(sesion_id)
        if es_moderador and sesion.moderador_id != usuario_id:
            raise SesionNoEncontrada(str(sesion_id))
        return self._vista(sesion, sesion.moderador_id == usuario_id)

    def guardar(
        self,
        sesion_id: UUID,
        moderador_id: UUID,
        fortalezas: list[str],
        mejoras: list[str],
        acciones: list[AccionMejora],
    ) -> VistaDebrief:
        sesion = self._del_moderador(sesion_id, moderador_id)
        ahora = self.reloj()
        debrief = self.debriefs.obtener(sesion.id) or Debrief(
            sesion_id=sesion.id,
            autor_id=moderador_id,
            creado_en=ahora,
            actualizado_en=ahora,
        )
        debrief.editar(fortalezas, mejoras, acciones, set(sesion.roles), ahora)
        self.debriefs.guardar(debrief)
        return self._vista(sesion, True)

    def completar(self, sesion_id: UUID, moderador_id: UUID) -> VistaDebrief:
        sesion = self._del_moderador(sesion_id, moderador_id)
        debrief = self.debriefs.obtener(sesion.id)
        if debrief is None:
            # Sin borrador guardado: completar() informa todo lo que falta.
            ahora = self.reloj()
            debrief = Debrief(sesion.id, moderador_id, ahora, ahora)
        debrief.completar(self.reloj())
        self.debriefs.guardar(debrief)
        return self._vista(sesion, True)

    def reabrir(self, sesion_id: UUID, moderador_id: UUID) -> VistaDebrief:
        sesion = self._del_moderador(sesion_id, moderador_id)
        debrief = self.debriefs.obtener(sesion.id)
        if debrief is None:
            raise SesionNoEncontrada(str(sesion_id))
        debrief.reabrir(self.reloj())
        self.debriefs.guardar(debrief)
        return self._vista(sesion, True)

    # --- apoyo ----------------------------------------------------------------------

    def _vista(self, sesion: SesionTabletop, puede_editar: bool) -> VistaDebrief:
        nombres = {r.codigo: r.nombre for r in self.catalogo.roles_ejercicio()}
        return VistaDebrief(
            sesion=sesion,
            debrief=self.debriefs.obtener(sesion.id),
            puede_editar=puede_editar,
            roles={c: nombres.get(c, c) for c in sesion.roles},
        )

    def _finalizada(self, sesion_id: UUID) -> SesionTabletop:
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.estado != EstadoSesion.FINALIZADA:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion

    def _del_moderador(self, sesion_id: UUID, moderador_id: UUID) -> SesionTabletop:
        sesion = self._finalizada(sesion_id)
        if sesion.moderador_id != moderador_id:
            raise SesionNoEncontrada(str(sesion_id))
        return sesion


# --- Resumen personal del participante ----------------------------------------------


@dataclass
class TareaResumen:
    inject_orden: int
    inject_titulo: str
    enunciado: str
    tipo: TipoTarea
    puntaje_maximo: int
    respondida: bool
    respuesta: str | None
    puntaje: float
    aciertos: list[str]
    faltantes: list[str]
    errores: list[str]
    # Selección múltiple: las opciones correctas, que ya se pueden mostrar.
    opciones_correctas: list[str]
    # Motivo del último ajuste del moderador, si lo hubo.
    ajuste_motivo: str | None


@dataclass
class ResumenParticipante:
    sesion: SesionTabletop
    rol_nombre: str
    puntaje: float
    maximo: int
    porcentaje: float
    posicion: int
    total_participantes: int
    tareas: list[TareaResumen]
    debrief: Debrief | None
    roles: dict[str, str]


class ServicioResumenParticipante:
    def __init__(
        self,
        sesiones: SesionRepository,
        respuestas: RespuestaRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
        almacen: AlmacenEnVivo,
        debriefs: DebriefRepository,
    ):
        self.sesiones = sesiones
        self.debriefs = debriefs
        self.registro = ServicioRegistroRespuestas(
            sesiones, respuestas, catalogo, usuarios, almacen
        )

    def resumen(self, sesion_id: UUID, usuario_id: UUID) -> ResumenParticipante:
        """Solo para un participante invitado y con la sesión ya finalizada."""
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.estado != EstadoSesion.FINALIZADA:
            raise SesionNoEncontrada(str(sesion_id))
        participante = next(
            (p for p in sesion.participantes if p.usuario_id == usuario_id), None
        )
        if participante is None:
            raise SesionNoEncontrada(str(sesion_id))

        acumulado = self.registro.acumulado_de(sesion)
        posicion = next(
            n
            for n, p in enumerate(acumulado.participantes, start=1)
            if p.usuario_id == usuario_id
        )
        mio = acumulado.participantes[posicion - 1]
        respuestas = {
            r.respuesta.tarea_id: r
            for r in self.registro.registro_de(sesion)
            if r.respuesta.usuario_id == usuario_id
        }
        injects = {i.id: i for i in sesion.injects}
        tareas = []
        for t in sesion.tareas:
            inject = injects.get(t.inject_id) if t.inject_id else None
            # Solo las tareas de su rol cuyo inject llegó a lanzarse.
            if t.rol_codigo != participante.rol_codigo or inject is None:
                continue
            if inject.orden > sesion.inject_actual:
                continue
            r = respuestas.get(t.id)
            ev = r.evaluacion if r else None
            tareas.append(
                TareaResumen(
                    inject_orden=inject.orden,
                    inject_titulo=inject.titulo,
                    enunciado=t.enunciado,
                    tipo=t.tipo,
                    puntaje_maximo=t.puntaje_maximo,
                    respondida=r is not None,
                    respuesta=(
                        r.respuesta.texto or ", ".join(r.opciones_elegidas_texto)
                    )
                    if r
                    else None,
                    puntaje=r.puntaje if r else 0.0,
                    aciertos=list(ev.aciertos) if ev else [],
                    faltantes=list(ev.faltantes) if ev else list(t.criterios),
                    errores=list(ev.errores) if ev else [],
                    opciones_correctas=[o.texto for o in t.opciones if o.correcta],
                    ajuste_motivo=r.ajustes[-1].motivo if r and r.ajustes else None,
                )
            )
        tareas.sort(key=lambda x: x.inject_orden)
        debrief = self.debriefs.obtener(sesion.id)
        return ResumenParticipante(
            sesion=sesion,
            rol_nombre=mio.rol_nombre,
            puntaje=mio.acumulado.puntaje,
            maximo=mio.acumulado.maximo,
            porcentaje=mio.acumulado.porcentaje,
            posicion=posicion,
            total_participantes=len(acumulado.participantes),
            tareas=tareas,
            # El participante solo ve lecciones ya cerradas por el moderador.
            debrief=debrief if debrief and debrief.completado else None,
            roles=self.registro.nombres_roles(),
        )
