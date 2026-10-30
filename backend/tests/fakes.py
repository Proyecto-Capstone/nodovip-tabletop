"""Dobles de prueba en memoria para los puertos (usuarios, accesos, sesiones, correo).

Permiten probar casos de uso y API sin PostgreSQL (corren igual en el CI).
"""

import copy
import threading
from datetime import UTC, datetime, timedelta

from app.domain.autenticacion import RegistroAcceso, ResultadoAcceso
from app.domain.sesiones import EstadoSesion
from app.ports.autenticacion import FiltroAccesos
from app.ports.correo import ErrorEnvioCorreo
from app.ports.respuesta_repository import RespuestaDuplicada
from app.ports.usuario_repository import FiltroUsuarios


class RepoUsuariosEnMemoria:
    def __init__(self):
        self.datos = {}

    def obtener_por_id(self, usuario_id):
        u = self.datos.get(usuario_id)
        return copy.deepcopy(u) if u else None

    def obtener_por_correo(self, correo):
        for u in self.datos.values():
            if u.correo.lower() == correo.lower():
                return copy.deepcopy(u)
        return None

    def listar(self, filtro: FiltroUsuarios | None = None):
        filtro = filtro or FiltroUsuarios()
        res = list(self.datos.values())
        if filtro.texto:
            t = filtro.texto.lower()
            res = [u for u in res if t in (u.nombre + u.correo).lower()]
        if filtro.rol:
            res = [u for u in res if u.rol == filtro.rol]
        if filtro.activo is not None:
            res = [u for u in res if u.activo == filtro.activo]
        return [copy.deepcopy(u) for u in sorted(res, key=lambda u: u.nombre)]

    def contar_activos(self, rol):
        return sum(1 for u in self.datos.values() if u.rol == rol and u.activo)

    def guardar(self, usuario):
        self.datos[usuario.id] = copy.deepcopy(usuario)
        return copy.deepcopy(usuario)

    def eliminar(self, usuario_id):
        self.datos.pop(usuario_id, None)


class HasherFalso:
    """Rápido y reversible; cuenta las verificaciones para probar el relleno."""

    def __init__(self):
        self.verificaciones = 0

    def hashear(self, contrasena):
        return f"hash::{contrasena[::-1]}"

    def verificar(self, contrasena, hash_guardado):
        self.verificaciones += 1
        return hash_guardado == self.hashear(contrasena)


class RepoAccesosEnMemoria:
    def __init__(self):
        self.registros: list[RegistroAcceso] = []

    def registrar(self, registro):
        registro = copy.deepcopy(registro)
        registro.id = len(self.registros) + 1
        self.registros.append(registro)

    def _recientes_primero(self):
        return sorted(self.registros, key=lambda r: (r.fecha_hora, r.id), reverse=True)

    def resultados_recientes(self, correo, desde, limite):
        return [
            r.resultado
            for r in self._recientes_primero()
            if r.correo == correo
            and r.fecha_hora >= desde
            and r.resultado != ResultadoAcceso.BLOQUEADO
        ][:limite]

    def listar(self, filtro: FiltroAccesos):
        res = self._recientes_primero()
        if filtro.usuario_id:
            res = [r for r in res if r.usuario_id == filtro.usuario_id]
        if filtro.correo:
            res = [r for r in res if filtro.correo.lower() in r.correo]
        if filtro.resultado:
            res = [r for r in res if r.resultado == filtro.resultado]
        if filtro.desde:
            res = [r for r in res if r.fecha_hora >= filtro.desde]
        if filtro.hasta:
            res = [r for r in res if r.fecha_hora <= filtro.hasta]
        return copy.deepcopy(res[: filtro.limite])


class RelojFalso:
    def __init__(self, inicio=datetime(2026, 10, 15, 9, 0, tzinfo=UTC)):
        self.ahora = inicio

    def __call__(self):
        return self.ahora

    def avanzar(self, **kwargs):
        self.ahora += timedelta(**kwargs)


# --- Sesiones e invitaciones (PB-05, PB-06) -----------------------------------


class RepoSesionesEnMemoria:
    def __init__(self):
        self.datos = {}
        self._lock_limite = threading.Lock()

    def obtener(self, sesion_id):
        s = self.datos.get(sesion_id)
        return copy.deepcopy(s) if s else None

    def listar_por_moderador(self, moderador_id):
        return [
            copy.deepcopy(s)
            for s in self.datos.values()
            if s.moderador_id == moderador_id
        ]

    def listar_por_participante(self, usuario_id):
        return [
            copy.deepcopy(s)
            for s in self.datos.values()
            if any(p.usuario_id == usuario_id for p in s.participantes)
        ]

    def listar_por_estados(self, estados):
        return [copy.deepcopy(s) for s in self.datos.values() if s.estado in estados]

    def guardar(self, sesion):
        self.datos[sesion.id] = copy.deepcopy(sesion)
        return copy.deepcopy(sesion)

    def iniciar_si_hay_cupo(self, sesion, maximo_activas):
        """Equivalente en memoria del advisory lock de PostgreSQL (PC-24):
        un `threading.Lock` basta porque todos los dobles de prueba viven
        en el mismo proceso."""
        with self._lock_limite:
            activas = sum(
                1 for s in self.datos.values() if s.estado == EstadoSesion.EN_CURSO
            )
            if activas >= maximo_activas:
                return None
            return self.guardar(sesion)

    def eliminar(self, sesion_id):
        self.datos.pop(sesion_id, None)


class EnviadorFalso:
    """Guarda los correos en vez de enviarlos; puede fallar para ciertos correos."""

    def __init__(self, fallar_para: set[str] | None = None):
        self.enviados = []
        self.fallar_para = fallar_para or set()

    def enviar(self, mensaje):
        if mensaje.destinatario_correo in self.fallar_para:
            raise ErrorEnvioCorreo("Brevo respondió 400: invalid email")
        self.enviados.append(mensaje)

    def para(self, correo):
        return [m for m in self.enviados if m.destinatario_correo == correo]


class RepoRespuestasEnMemoria:
    """Como la tabla respuesta: solo inserta y rechaza la segunda respuesta."""

    def __init__(self):
        self.datos = []
        self.ajustes = []

    def guardar(self, respuesta):
        if any(
            r.tarea_id == respuesta.tarea_id and r.usuario_id == respuesta.usuario_id
            for r in self.datos
        ):
            raise RespuestaDuplicada(str(respuesta.tarea_id))
        self.datos.append(copy.deepcopy(respuesta))
        return copy.deepcopy(respuesta)

    def de_participante(self, sesion_id, usuario_id):
        return [
            copy.deepcopy(r)
            for r in self.datos
            if r.sesion_id == sesion_id and r.usuario_id == usuario_id
        ]

    def de_sesion(self, sesion_id):
        return sorted(
            (copy.deepcopy(r) for r in self.datos if r.sesion_id == sesion_id),
            key=lambda r: r.recibida_en,
        )

    def obtener(self, respuesta_id):
        return next(
            (copy.deepcopy(r) for r in self.datos if r.id == respuesta_id), None
        )

    def agregar_ajuste(self, ajuste, sesion_id):
        self.ajustes.append((sesion_id, copy.deepcopy(ajuste)))
        return copy.deepcopy(ajuste)

    def ajustes_de_sesion(self, sesion_id):
        return sorted(
            (copy.deepcopy(a) for s, a in self.ajustes if s == sesion_id),
            key=lambda a: a.creado_en,
        )
