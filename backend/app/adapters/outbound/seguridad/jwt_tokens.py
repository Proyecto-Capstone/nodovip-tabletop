"""Tokens de sesión JWT firmados con HS256 (PB-01). Adaptador de salida.

El token solo lleva el id del usuario (`sub`) y su vigencia. El rol y el estado
se leen de la base en cada request, así que no viajan en el token.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

ALGORITMO = "HS256"
VIGENCIA = timedelta(hours=8)


class JwtTokens:
    def __init__(
        self,
        secreto: str,
        vigencia: timedelta = VIGENCIA,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.secreto = secreto
        self.vigencia = vigencia
        self.reloj = reloj

    def emitir(self, usuario_id: UUID) -> str:
        ahora = self.reloj()
        datos = {"sub": str(usuario_id), "iat": ahora, "exp": ahora + self.vigencia}
        return jwt.encode(datos, self.secreto, algorithm=ALGORITMO)

    def validar(self, token: str) -> UUID | None:
        try:
            datos = jwt.decode(
                token,
                self.secreto,
                algorithms=[ALGORITMO],
                options={"require": ["sub", "exp", "iat"]},
            )
            return UUID(datos["sub"])
        except (jwt.InvalidTokenError, ValueError):
            return None
