"""Tareas del participante y envío de respuestas (PB-08, RF-02).

Enrutamiento por rol: cada participante ve solo las tareas de su rol cuyo
inject ya se lanzó. Responde una vez cada una, dentro del tiempo límite.

PB-09: registro trazable. El moderador consulta, en solo lectura, todas las
respuestas de su sesión con participante, rol, inject, tarea y hora.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.en_vivo import ServicioEnVivo
from app.application.sesiones import SesionNoEncontrada
from app.domain.en_vivo import EstadoEnVivo
from app.domain.respuestas import (
    EstadoTarea,
    Respuesta,
    errores_de_contenido,
    estado_tarea,
    exigir_a_tiempo,
)
from app.domain.sesiones import (
    EstadoSesion,
    ParticipanteSesion,
    ReglaSesionError,
    SesionTabletop,
    TareaSesion,
)
from app.ports.en_vivo import AlmacenEnVivo
from app.ports.escenario_repository import CatalogoRepository
from app.ports.respuesta_repository import RespuestaRepository
from app.ports.sesion_repository import SesionRepository
from app.ports.usuario_repository import UsuarioRepository


class TareaNoEncontrada(LookupError):
    pass


def _ahora() -> datetime:
    return datetime.now(UTC)


@dataclass
class TareaDelParticipante:
    tarea: TareaSesion
    inject_orden: int
    segundos_restantes: int
    estado: EstadoTarea
    respuesta: Respuesta | None


class ServicioRespuestas:
    def __init__(
        self,
        sesiones: SesionRepository,
        almacen: AlmacenEnVivo,
        respuestas: RespuestaRepository,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.sesiones = sesiones
        self.respuestas = respuestas
        self.reloj = reloj
        self.en_vivo = ServicioEnVivo(sesiones, almacen, reloj)

    def tareas(self, sesion_id: UUID, usuario_id: UUID) -> list[TareaDelParticipante]:
        """Tareas del rol del participante ya lanzadas, la más reciente primero."""
        sesion, participante = self._del_participante(sesion_id, usuario_id)
        estado = self.en_vivo.estado_de(sesion)
        if estado is None:
            return []
        hechas = {
            r.tarea_id: r
            for r in self.respuestas.de_participante(sesion.id, usuario_id)
        }
        ahora = self.reloj()
        resultado = []
        for tarea, orden in self._lanzadas_del_rol(sesion, participante, estado):
            usados = estado.segundos_desde_lanzamiento(orden, ahora) or 0
            restantes = max(0, tarea.tiempo_limite_segundos - usados)
            respuesta = hechas.get(tarea.id)
            resultado.append(
                TareaDelParticipante(
                    tarea=tarea,
                    inject_orden=orden,
                    segundos_restantes=0 if respuesta else restantes,
                    estado=estado_tarea(respuesta, restantes),
                    respuesta=respuesta,
                )
            )
        resultado.sort(key=lambda t: -t.inject_orden)
        return resultado

    def responder(
        self,
        sesion_id: UUID,
        usuario_id: UUID,
        tarea_id: UUID,
        texto: str | None,
        opciones: list[int],
    ) -> Respuesta:
        sesion, participante = self._del_participante(sesion_id, usuario_id)
        estado = self.en_vivo.estado_de(sesion)
        if estado is None:
            raise ReglaSesionError(["La sesión no está en curso"])
        if estado.pausada:
            raise ReglaSesionError(["La sesión está en pausa: espera a que se reanude"])
        lanzadas = {
            t.id: (t, o)
            for t, o in self._lanzadas_del_rol(sesion, participante, estado)
        }
        if tarea_id not in lanzadas:
            # Tarea de otro rol o de un inject que todavía no se lanzó.
            raise TareaNoEncontrada(str(tarea_id))
        tarea, orden = lanzadas[tarea_id]
        ahora = self.reloj()
        usados = estado.segundos_desde_lanzamiento(orden, ahora) or 0
        exigir_a_tiempo(tarea, usados)
        errores = errores_de_contenido(tarea, texto, opciones)
        if errores:
            raise ReglaSesionError(errores)
        # Si ya respondió, el repositorio lanza RespuestaDuplicada.
        return self.respuestas.guardar(
            Respuesta(
                sesion_id=sesion.id,
                tarea_id=tarea.id,
                inject_id=tarea.inject_id,
                usuario_id=usuario_id,
                rol_codigo=participante.rol_codigo,
                recibida_en=ahora,
                segundos_usados=usados,
                texto=texto.strip() if texto else None,
                opciones_elegidas=opciones,
            )
        )

    # --- apoyo ----------------------------------------------------------------------

    def _del_participante(
        self, sesion_id: UUID, usuario_id: UUID
    ) -> tuple[SesionTabletop, ParticipanteSesion]:
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or not sesion.visible_para(usuario_id):
            raise SesionNoEncontrada(str(sesion_id))
        participante = sesion.participante_de(usuario_id)
        assert participante is not None
        return sesion, participante

    @staticmethod
    def _lanzadas_del_rol(
        sesion: SesionTabletop, participante: ParticipanteSesion, estado: EstadoEnVivo
    ) -> list[tuple[TareaSesion, int]]:
        if sesion.estado != EstadoSesion.EN_CURSO:
            return []
        orden_de = {i.id: i.orden for i in sesion.injects}
        return [
            (t, orden_de[t.inject_id])
            for t in sesion.tareas
            if t.rol_codigo == participante.rol_codigo
            and t.inject_id in orden_de
            and orden_de[t.inject_id] <= estado.inject_actual
        ]


# --- Registro de respuestas de la sesión (PB-09) -------------------------------------


@dataclass
class RespuestaRegistrada:
    """Una respuesta con todo lo necesario para auditarla."""

    respuesta: Respuesta
    participante_nombre: str
    participante_correo: str
    rol_nombre: str
    inject_orden: int
    inject_titulo: str
    tarea: TareaSesion

    @property
    def opciones_elegidas_texto(self) -> list[str]:
        opciones = self.tarea.opciones
        return [
            opciones[i].texto
            for i in self.respuesta.opciones_elegidas
            if 0 <= i < len(opciones)
        ]


class ServicioRegistroRespuestas:
    """Consulta de solo lectura: no hay forma de modificar ni borrar respuestas."""

    def __init__(
        self,
        sesiones: SesionRepository,
        respuestas: RespuestaRepository,
        catalogo: CatalogoRepository,
        usuarios: UsuarioRepository,
    ):
        self.sesiones = sesiones
        self.respuestas = respuestas
        self.catalogo = catalogo
        self.usuarios = usuarios

    def de_sesion(
        self, sesion_id: UUID, moderador_id: UUID
    ) -> list[RespuestaRegistrada]:
        """Respuestas de la sesión en orden de llegada. Solo para su moderador."""
        sesion = self.sesiones.obtener(sesion_id)
        if sesion is None or sesion.moderador_id != moderador_id:
            raise SesionNoEncontrada(str(sesion_id))
        roles = {r.codigo: r.nombre for r in self.catalogo.roles_ejercicio()}
        injects = {i.id: i for i in sesion.injects}
        tareas = {t.id: t for t in sesion.tareas}
        personas: dict[UUID, tuple[str, str]] = {}
        resultado = []
        for r in self.respuestas.de_sesion(sesion.id):
            if r.usuario_id not in personas:
                u = self.usuarios.obtener_por_id(r.usuario_id)
                personas[r.usuario_id] = (u.nombre, u.correo) if u else ("—", "—")
            nombre, correo = personas[r.usuario_id]
            inject = injects[r.inject_id]
            resultado.append(
                RespuestaRegistrada(
                    respuesta=r,
                    participante_nombre=nombre,
                    participante_correo=correo,
                    rol_nombre=roles.get(r.rol_codigo, r.rol_codigo),
                    inject_orden=inject.orden,
                    inject_titulo=inject.titulo,
                    tarea=tareas[r.tarea_id],
                )
            )
        return resultado
