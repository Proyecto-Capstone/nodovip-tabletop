"""Entidades y reglas de negocio de las sesiones tabletop (M1, RF-01, PB-05).

Una sesión es la instancia que el moderador diseña a partir de un escenario
publicado: copia sus roles, injects y tareas para poder ajustarlos sin tocar el
escenario original, asigna un participante a cada rol, ubica cada tarea en un
inject, define los criterios y pesos de puntuación y programa fecha y duración.

Núcleo de dominio: no depende de FastAPI, SQLAlchemy ni de ningún framework.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.escenarios import Escenario, EstadoEscenario, Inject, Nivel

MIN_OPCIONES = 2


class EstadoSesion(StrEnum):
    BORRADOR = "borrador"
    PROGRAMADA = "programada"
    # Los usa el motor en tiempo real (PB-07).
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"


ESTADOS_EDITABLES = (EstadoSesion.BORRADOR, EstadoSesion.PROGRAMADA)


class TipoTarea(StrEnum):
    TEXTO_LIBRE = "texto_libre"
    SELECCION_MULTIPLE = "seleccion_multiple"


class ReglaSesionError(ValueError):
    """Una sesión no cumple una regla de negocio de RF-01."""

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("; ".join(errores))


@dataclass
class OpcionRespuesta:
    texto: str
    correcta: bool = False


@dataclass
class TareaSesion:
    """Tarea que recibe un rol durante un inject de la sesión.

    Texto libre se evalúa con `criterios`; selección múltiple, con las opciones
    marcadas como correctas (PB-10).
    """

    enunciado: str
    rol_codigo: str
    dificultad: Nivel
    criterios: list[str]
    inject_id: UUID | None = None
    tipo: TipoTarea = TipoTarea.TEXTO_LIBRE
    opciones: list[OpcionRespuesta] = field(default_factory=list)
    puntaje_maximo: int = 10
    tiempo_limite_segundos: int = 300
    respuesta_esperada: str | None = None
    id: UUID = field(default_factory=uuid4)

    def errores_para_programar(self) -> list[str]:
        inicio = self.enunciado[:40]
        if self.tipo == TipoTarea.SELECCION_MULTIPLE:
            errores = []
            if len(self.opciones) < MIN_OPCIONES:
                errores.append(
                    f'La tarea "{inicio}" necesita al menos {MIN_OPCIONES} opciones'
                )
            if not any(o.correcta for o in self.opciones):
                errores.append(f'La tarea "{inicio}" no tiene una opción correcta')
            return errores
        if not self.criterios:
            return [f'La tarea "{inicio}" necesita al menos un criterio de evaluación']
        return []


@dataclass
class PesosPuntuacion:
    """Cuánto pesa cada aspecto al evaluar una respuesta (RF-03). Suman 100."""

    completitud: int = 40
    precision: int = 40
    tiempo: int = 20

    def errores(self) -> list[str]:
        valores = (self.completitud, self.precision, self.tiempo)
        if any(v < 0 for v in valores):
            return ["Los pesos de puntuación no pueden ser negativos"]
        if sum(valores) != 100:
            return [f"Los pesos de puntuación deben sumar 100 (suman {sum(valores)})"]
        return []


class EstadoInvitacion(StrEnum):
    """Seguimiento de la invitación por correo (PB-06)."""

    PENDIENTE = "pendiente"
    ENVIADA = "enviada"
    FALLIDA = "fallida"
    ACEPTADA = "aceptada"


# Se (re)envían al programar o cuando el moderador lo pide en el paso 6.
POR_ENVIAR = (EstadoInvitacion.PENDIENTE, EstadoInvitacion.FALLIDA)
# Estados en los que el participante ve la sesión y puede aceptar.
VISIBLES_PARA_PARTICIPANTE = (EstadoSesion.PROGRAMADA, EstadoSesion.EN_CURSO)


@dataclass
class ParticipanteSesion:
    """Usuario invitado a la sesión con el rol de ejercicio que asumirá."""

    usuario_id: UUID
    rol_codigo: str
    invitacion: EstadoInvitacion = EstadoInvitacion.PENDIENTE
    invitacion_enviada_en: datetime | None = None
    invitacion_aceptada_en: datetime | None = None
    invitacion_error: str | None = None

    def marcar_enviada(self, ahora: datetime) -> None:
        # Si ya aceptó (p. ej. con un reenvío), no se retrocede.
        if self.invitacion != EstadoInvitacion.ACEPTADA:
            self.invitacion = EstadoInvitacion.ENVIADA
        self.invitacion_enviada_en = ahora
        self.invitacion_error = None

    def marcar_fallida(self, error: str) -> None:
        if self.invitacion != EstadoInvitacion.ACEPTADA:
            self.invitacion = EstadoInvitacion.FALLIDA
        self.invitacion_error = error[:300]

    def mismo_puesto(self, otro: "ParticipanteSesion") -> bool:
        return self.usuario_id == otro.usuario_id and self.rol_codigo == otro.rol_codigo


@dataclass
class SesionTabletop:
    nombre: str
    escenario_id: UUID
    moderador_id: UUID
    roles: list[str]
    injects: list[Inject] = field(default_factory=list)
    tareas: list[TareaSesion] = field(default_factory=list)
    participantes: list[ParticipanteSesion] = field(default_factory=list)
    pesos: PesosPuntuacion = field(default_factory=PesosPuntuacion)
    fecha_programada: datetime | None = None
    duracion_minutos: int | None = None
    estado: EstadoSesion = EstadoSesion.BORRADOR
    # Ejecución en vivo (PB-07). Se guardan para reconstruir el estado si
    # Redis se pierde y como registro de la sesión ya realizada.
    iniciada_en: datetime | None = None
    finalizada_en: datetime | None = None
    inject_actual: int = 0
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def desde_escenario(
        cls, escenario: Escenario, moderador_id: UUID, nombre: str | None = None
    ) -> "SesionTabletop":
        """Crea un borrador copiando el contenido del escenario publicado.

        Las tareas de cada rol se reparten en orden entre los injects (la
        primera del rol en el inject 1, la segunda en el 2...). El moderador
        puede moverlas después.
        """
        if escenario.estado != EstadoEscenario.PUBLICADO:
            raise ReglaSesionError(["Solo se puede usar un escenario publicado"])
        # Copias con id nuevo: editar la sesión no modifica el escenario.
        injects = [
            replace(i, id=uuid4())
            for i in sorted(escenario.injects, key=lambda i: i.orden)
        ]
        tareas: list[TareaSesion] = []
        usadas_por_rol: dict[str, int] = {}
        for t in escenario.tareas:
            n = usadas_por_rol.get(t.rol_codigo, 0)
            usadas_por_rol[t.rol_codigo] = n + 1
            tareas.append(
                TareaSesion(
                    enunciado=t.enunciado,
                    rol_codigo=t.rol_codigo,
                    dificultad=t.dificultad,
                    criterios=list(t.criterios),
                    inject_id=injects[n % len(injects)].id if injects else None,
                    puntaje_maximo=t.puntaje_maximo,
                    tiempo_limite_segundos=t.tiempo_limite_segundos,
                    respuesta_esperada=t.respuesta_esperada,
                )
            )
        return cls(
            nombre=nombre or escenario.nombre,
            escenario_id=escenario.id,
            moderador_id=moderador_id,
            roles=list(escenario.roles),
            injects=injects,
            tareas=tareas,
        )

    @property
    def puntaje_maximo_total(self) -> int:
        """Puntuación máxima posible, calculada automáticamente (RF-01)."""
        return sum(t.puntaje_maximo for t in self.tareas)

    def validar_consistencia(self) -> None:
        """Reglas que se cumplen siempre, incluso en borrador."""
        errores: list[str] = []
        if not self.nombre.strip():
            errores.append("La sesión debe tener un nombre")
        if len(set(self.roles)) != len(self.roles):
            errores.append("Hay roles repetidos")
        roles = set(self.roles)
        ajenas = sorted({t.rol_codigo for t in self.tareas} - roles)
        if ajenas:
            errores.append(
                "Hay tareas para roles que no están en la sesión: " + ", ".join(ajenas)
            )
        ordenes = [i.orden for i in self.injects]
        if len(set(ordenes)) != len(ordenes):
            errores.append("Hay injects con el mismo orden")
        injects = {i.id for i in self.injects}
        if any(t.inject_id and t.inject_id not in injects for t in self.tareas):
            errores.append("Hay tareas asignadas a un inject que no está en la sesión")
        if any(t.tipo == TipoTarea.TEXTO_LIBRE and t.opciones for t in self.tareas):
            errores.append("Las tareas de texto libre no llevan opciones")
        usuarios = [p.usuario_id for p in self.participantes]
        if len(set(usuarios)) != len(usuarios):
            errores.append("Un participante solo puede tener un rol en la sesión")
        sin_rol = sorted({p.rol_codigo for p in self.participantes} - roles)
        if sin_rol:
            errores.append(
                "Hay participantes con roles que no están en la sesión: "
                + ", ".join(sin_rol)
            )
        errores += self.pesos.errores()
        if errores:
            raise ReglaSesionError(errores)

    def errores_para_programar(self, ahora: datetime) -> list[str]:
        """Devuelve las reglas de RF-01 que la sesión todavía no cumple."""
        errores: list[str] = []
        if not self.roles:
            errores.append("Debe tener al menos un rol")
        if not self.injects:
            errores.append("Debe tener al menos un inject")
        roles_con_tareas = {t.rol_codigo for t in self.tareas}
        sin_tareas = [r for r in self.roles if r not in roles_con_tareas]
        if sin_tareas:
            errores.append("Faltan tareas para los roles: " + ", ".join(sin_tareas))
        if any(t.inject_id is None for t in self.tareas):
            errores.append("Todas las tareas deben estar asignadas a un inject")
        for t in self.tareas:
            errores += t.errores_para_programar()
        roles_cubiertos = {p.rol_codigo for p in self.participantes}
        sin_participante = [r for r in self.roles if r not in roles_cubiertos]
        if sin_participante:
            errores.append(
                "Falta al menos un participante para los roles: "
                + ", ".join(sin_participante)
            )
        if self.fecha_programada is None:
            errores.append("Debe tener fecha y hora programadas")
        elif self.fecha_programada <= ahora:
            errores.append("La fecha programada debe ser futura")
        if not self.duracion_minutos:
            errores.append("Debe tener una duración")
        return errores

    def programar(self, ahora: datetime) -> None:
        """Pasa de borrador a programada: queda lista para iniciarse (PB-07)."""
        if self.estado != EstadoSesion.BORRADOR:
            raise ReglaSesionError(["Solo se puede programar una sesión en borrador"])
        self.validar_consistencia()
        errores = self.errores_para_programar(ahora)
        if errores:
            raise ReglaSesionError(errores)
        self.estado = EstadoSesion.PROGRAMADA

    def reemplazar_diseno(self, nuevo: "SesionTabletop", ahora: datetime) -> None:
        """Guarda cambios del diseñador. Si ya está programada, debe seguir
        siendo programable."""
        if self.estado not in ESTADOS_EDITABLES:
            raise ReglaSesionError(["La sesión ya no se puede editar"])
        nuevo.validar_consistencia()
        if self.estado == EstadoSesion.PROGRAMADA:
            errores = nuevo.errores_para_programar(ahora)
            if errores:
                raise ReglaSesionError(errores)
        # La invitación se conserva si el participante sigue con el mismo rol;
        # si es nuevo o cambió de rol, queda pendiente de enviar.
        for p in nuevo.participantes:
            anterior = next((a for a in self.participantes if a.mismo_puesto(p)), None)
            p.invitacion = (
                anterior.invitacion if anterior else EstadoInvitacion.PENDIENTE
            )
            p.invitacion_enviada_en = (
                anterior.invitacion_enviada_en if anterior else None
            )
            p.invitacion_aceptada_en = (
                anterior.invitacion_aceptada_en if anterior else None
            )
            p.invitacion_error = anterior.invitacion_error if anterior else None
        self.nombre = nuevo.nombre
        self.roles = nuevo.roles
        self.injects = nuevo.injects
        self.tareas = nuevo.tareas
        self.participantes = nuevo.participantes
        self.pesos = nuevo.pesos
        self.fecha_programada = nuevo.fecha_programada
        self.duracion_minutos = nuevo.duracion_minutos

    # --- Invitaciones y acceso del participante (PB-06) ------------------------

    def participante_de(self, usuario_id: UUID) -> ParticipanteSesion | None:
        return next((p for p in self.participantes if p.usuario_id == usuario_id), None)

    def visible_para(self, usuario_id: UUID) -> bool:
        """Un participante solo ve sesiones a las que fue invitado y que ya
        fueron programadas (un borrador todavía puede cambiar)."""
        return (
            self.estado in VISIBLES_PARA_PARTICIPANTE
            and self.participante_de(usuario_id) is not None
        )

    def invitaciones_por_enviar(self) -> list[ParticipanteSesion]:
        if self.estado not in VISIBLES_PARA_PARTICIPANTE:
            raise ReglaSesionError(
                ["Las invitaciones se envían cuando la sesión está programada"]
            )
        return [p for p in self.participantes if p.invitacion in POR_ENVIAR]

    def aceptar_invitacion(self, usuario_id: UUID, ahora: datetime) -> None:
        participante = self.participante_de(usuario_id)
        if participante is None or not self.visible_para(usuario_id):
            raise ReglaSesionError(["No tienes una invitación a esta sesión"])
        if participante.invitacion != EstadoInvitacion.ACEPTADA:
            participante.invitacion = EstadoInvitacion.ACEPTADA
            participante.invitacion_aceptada_en = ahora

    # --- Ejecución en vivo (PB-07) ----------------------------------------------

    def iniciar(self, ahora: datetime) -> None:
        """El moderador abre la sesión programada: pasa a en curso."""
        if self.estado != EstadoSesion.PROGRAMADA:
            raise ReglaSesionError(["Solo se puede iniciar una sesión programada"])
        self.estado = EstadoSesion.EN_CURSO
        self.iniciada_en = ahora
        self.inject_actual = 0

    def finalizar(self, ahora: datetime, inject_actual: int) -> None:
        if self.estado != EstadoSesion.EN_CURSO:
            raise ReglaSesionError(["Solo se puede cerrar una sesión en curso"])
        self.estado = EstadoSesion.FINALIZADA
        self.finalizada_en = ahora
        self.inject_actual = inject_actual
