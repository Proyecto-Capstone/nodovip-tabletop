"""Esquemas de entrada y salida de la API de sesiones (PB-05)."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.adapters.inbound.api.schemas_escenarios import InjectSalida
from app.domain.escenarios import Inject, Nivel
from app.domain.sesiones import (
    EstadoInvitacion,
    EstadoSesion,
    OpcionRespuesta,
    ParticipanteSesion,
    PesosPuntuacion,
    SesionTabletop,
    TareaSesion,
    TipoTarea,
)
from app.domain.usuarios import Usuario


class SesionNueva(BaseModel):
    """Paso 1: elegir el escenario. El nombre por defecto es el del escenario."""

    model_config = ConfigDict(str_strip_whitespace=True)

    escenario_id: UUID
    nombre: str | None = Field(default=None, min_length=3, max_length=150)
    # Organización para la que se hace el ejercicio (PB-14). Opcional.
    cliente: str | None = Field(default=None, max_length=120)


class InjectSesionEntrada(BaseModel):
    """El cliente manda el id (también de los injects nuevos) para que las
    tareas puedan apuntar a su inject en el mismo request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    titulo: str = Field(min_length=3, max_length=150)
    descripcion: str = Field(min_length=10, max_length=5000)
    minuto_sugerido: int | None = Field(default=None, ge=0, le=600)


class OpcionEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    texto: str = Field(min_length=1, max_length=300)
    correcta: bool = False


class TareaSesionEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID | None = None
    inject_id: UUID | None = None
    rol_codigo: str = Field(min_length=2, max_length=40)
    tipo: TipoTarea = TipoTarea.TEXTO_LIBRE
    enunciado: str = Field(min_length=10, max_length=2000)
    opciones: list[OpcionEntrada] = Field(default_factory=list, max_length=8)
    criterios: list[str] = Field(default_factory=list, max_length=10)
    dificultad: Nivel = Nivel.MEDIO
    puntaje_maximo: int = Field(default=10, ge=1, le=100)
    tiempo_limite_segundos: int = Field(default=300, ge=30, le=3600)
    respuesta_esperada: str | None = Field(default=None, max_length=5000)


class ParticipanteEntrada(BaseModel):
    usuario_id: UUID
    rol_codigo: str = Field(min_length=2, max_length=40)


class PesosEntrada(BaseModel):
    completitud: int = Field(default=40, ge=0, le=100)
    precision: int = Field(default=40, ge=0, le=100)
    tiempo: int = Field(default=20, ge=0, le=100)


class SesionDiseno(BaseModel):
    """Diseño completo que guarda el asistente (pasos 2 a 5)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=3, max_length=150)
    cliente: str | None = Field(default=None, max_length=120)
    roles: list[str] = Field(default_factory=list, max_length=15)
    injects: list[InjectSesionEntrada] = Field(default_factory=list, max_length=30)
    tareas: list[TareaSesionEntrada] = Field(default_factory=list, max_length=100)
    participantes: list[ParticipanteEntrada] = Field(
        default_factory=list, max_length=100
    )
    pesos: PesosEntrada = Field(default_factory=PesosEntrada)
    fecha_programada: AwareDatetime | None = None
    duracion_minutos: int | None = Field(default=None, ge=15, le=480)

    def a_dominio(self, actual: SesionTabletop) -> SesionTabletop:
        """El orden de los injects es su posición en la lista (1, 2, 3...)."""
        return SesionTabletop(
            id=actual.id,
            escenario_id=actual.escenario_id,
            moderador_id=actual.moderador_id,
            nombre=self.nombre,
            cliente=self.cliente,
            roles=self.roles,
            injects=[
                Inject(
                    id=i.id,
                    orden=pos,
                    titulo=i.titulo,
                    descripcion=i.descripcion,
                    minuto_sugerido=i.minuto_sugerido,
                )
                for pos, i in enumerate(self.injects, start=1)
            ],
            tareas=[
                TareaSesion(
                    inject_id=t.inject_id,
                    rol_codigo=t.rol_codigo,
                    tipo=t.tipo,
                    enunciado=t.enunciado,
                    opciones=[OpcionRespuesta(o.texto, o.correcta) for o in t.opciones],
                    criterios=[c.strip() for c in t.criterios if c.strip()],
                    dificultad=t.dificultad,
                    puntaje_maximo=t.puntaje_maximo,
                    tiempo_limite_segundos=t.tiempo_limite_segundos,
                    respuesta_esperada=t.respuesta_esperada,
                    **({"id": t.id} if t.id else {}),
                )
                for t in self.tareas
            ],
            participantes=[
                ParticipanteSesion(p.usuario_id, p.rol_codigo)
                for p in self.participantes
            ],
            pesos=PesosPuntuacion(**self.pesos.model_dump()),
            fecha_programada=self.fecha_programada,
            duracion_minutos=self.duracion_minutos,
        )


class OpcionSalida(BaseModel):
    texto: str
    correcta: bool


class TareaSesionSalida(BaseModel):
    id: UUID
    inject_id: UUID | None
    rol_codigo: str
    tipo: TipoTarea
    enunciado: str
    opciones: list[OpcionSalida]
    criterios: list[str]
    dificultad: Nivel
    puntaje_maximo: int
    tiempo_limite_segundos: int
    respuesta_esperada: str | None

    @classmethod
    def desde(cls, t: TareaSesion) -> "TareaSesionSalida":
        datos = vars(t) | {"opciones": [OpcionSalida(**vars(o)) for o in t.opciones]}
        return cls(**datos)


class ParticipanteSalida(BaseModel):
    usuario_id: UUID
    rol_codigo: str
    invitacion: EstadoInvitacion
    invitacion_enviada_en: datetime | None
    invitacion_aceptada_en: datetime | None
    invitacion_error: str | None


class PesosSalida(BaseModel):
    completitud: int
    precision: int
    tiempo: int


class SesionResumen(BaseModel):
    id: UUID
    nombre: str
    cliente: str | None
    escenario_id: UUID
    estado: EstadoSesion
    fecha_programada: datetime | None
    duracion_minutos: int | None
    roles: list[str]
    total_participantes: int
    puntaje_maximo_total: int

    @classmethod
    def desde(cls, s: SesionTabletop) -> "SesionResumen":
        return cls(
            id=s.id,
            nombre=s.nombre,
            cliente=s.cliente,
            escenario_id=s.escenario_id,
            estado=s.estado,
            fecha_programada=s.fecha_programada,
            duracion_minutos=s.duracion_minutos,
            roles=s.roles,
            total_participantes=len(s.participantes),
            puntaje_maximo_total=s.puntaje_maximo_total,
        )


class SesionDetalle(SesionResumen):
    injects: list[InjectSalida]
    tareas: list[TareaSesionSalida]
    participantes: list[ParticipanteSalida]
    pesos: PesosSalida
    pendientes_para_programar: list[str]

    @classmethod
    def desde(cls, s: SesionTabletop, ahora: datetime) -> "SesionDetalle":
        return cls(
            **SesionResumen.desde(s).model_dump(),
            injects=[InjectSalida(**vars(i)) for i in s.injects],
            tareas=[TareaSesionSalida.desde(t) for t in s.tareas],
            participantes=[ParticipanteSalida(**vars(p)) for p in s.participantes],
            pesos=PesosSalida(**vars(s.pesos)),
            pendientes_para_programar=s.errores_para_programar(ahora),
        )


class ParticipanteDisponible(BaseModel):
    """Solo lo necesario para asignar roles: el moderador no gestiona usuarios."""

    id: UUID
    nombre: str
    correo: str

    @classmethod
    def desde(cls, u: Usuario) -> "ParticipanteDisponible":
        return cls(id=u.id, nombre=u.nombre, correo=u.correo)
