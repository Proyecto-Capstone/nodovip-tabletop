"""Casos de uso de autenticación e historial de accesos (PB-01, RNF-01).

Coordina dominio y puertos. No conoce HTTP, cookies, SQLAlchemy, bcrypt ni JWT.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.autenticacion import (
    MAX_INTENTOS_FALLIDOS,
    VENTANA_BLOQUEO,
    RegistroAcceso,
    ResultadoAcceso,
    esta_bloqueado,
)
from app.domain.usuarios import Usuario, normalizar_correo
from app.ports.autenticacion import (
    EmisorTokens,
    FiltroAccesos,
    RegistroAccesoRepository,
)
from app.ports.usuario_repository import HasherContrasenas, UsuarioRepository

# Columnas varchar(255) del historial.
_LARGO_MAXIMO = 255
CLAVE_RELLENO = "no-es-la-clave-de-nadie-solo-iguala-el-tiempo"


class CredencialesInvalidas(Exception):
    """Correo inexistente, contraseña incorrecta o cuenta inactiva.

    Es una sola excepción a propósito: la API responde lo mismo en los tres
    casos para no revelar qué correos existen. El motivo real queda en el
    historial de accesos.
    """


class AccesoBloqueado(Exception):
    pass


@dataclass
class SesionIniciada:
    usuario: Usuario
    token: str


def _ahora() -> datetime:
    return datetime.now(UTC)


class ServicioAutenticacion:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        accesos: RegistroAccesoRepository,
        hasher: HasherContrasenas,
        tokens: EmisorTokens,
        hash_relleno: str | None = None,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self.usuarios = usuarios
        self.accesos = accesos
        self.hasher = hasher
        self.tokens = tokens
        self._hash_relleno = hash_relleno
        self.reloj = reloj

    def iniciar_sesion(
        self, correo: str, contrasena: str, ip: str, user_agent: str | None = None
    ) -> SesionIniciada:
        correo = normalizar_correo(correo)[:_LARGO_MAXIMO]
        usuario = self.usuarios.obtener_por_correo(correo)

        def registrar(resultado: ResultadoAcceso) -> None:
            self.accesos.registrar(
                RegistroAcceso(
                    correo=correo,
                    resultado=resultado,
                    ip=ip,
                    usuario_id=usuario.id if usuario else None,
                    user_agent=user_agent[:_LARGO_MAXIMO] if user_agent else None,
                    fecha_hora=self.reloj(),
                )
            )

        if self._bloqueado(correo):
            registrar(ResultadoAcceso.BLOQUEADO)
            raise AccesoBloqueado(correo)

        # Si el correo no existe se verifica igual contra un hash de relleno:
        # la respuesta tarda lo mismo y no delata qué correos están registrados.
        hash_guardado = usuario.password_hash if usuario else self.hash_relleno
        clave_correcta = self.hasher.verificar(contrasena, hash_guardado)

        if usuario is None or not clave_correcta:
            registrar(ResultadoAcceso.CREDENCIALES_INVALIDAS)
            raise CredencialesInvalidas()
        if not usuario.activo:
            registrar(ResultadoAcceso.USUARIO_INACTIVO)
            raise CredencialesInvalidas()

        registrar(ResultadoAcceso.EXITOSO)
        return SesionIniciada(usuario=usuario, token=self.tokens.emitir(usuario.id))

    def usuario_desde_token(self, token: str) -> Usuario | None:
        """Usuario dueño del token, recargado de la base en cada request.

        Así una cuenta desactivada o con otro rol deja de tener los permisos
        anteriores de inmediato, sin esperar a que el token venza.
        """
        usuario_id: UUID | None = self.tokens.validar(token)
        if usuario_id is None:
            return None
        usuario = self.usuarios.obtener_por_id(usuario_id)
        if usuario is None or not usuario.activo:
            return None
        return usuario

    def listar_accesos(self, filtro: FiltroAccesos) -> list[RegistroAcceso]:
        return self.accesos.listar(filtro)

    # --- reglas ----------------------------------------------------------------

    @property
    def hash_relleno(self) -> str:
        if self._hash_relleno is None:
            self._hash_relleno = self.hasher.hashear(CLAVE_RELLENO)
        return self._hash_relleno

    def _bloqueado(self, correo: str) -> bool:
        recientes = self.accesos.resultados_recientes(
            correo,
            desde=self.reloj() - VENTANA_BLOQUEO,
            limite=MAX_INTENTOS_FALLIDOS,
        )
        return esta_bloqueado(recientes)
