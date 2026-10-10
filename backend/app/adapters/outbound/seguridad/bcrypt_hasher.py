"""Hash de contraseñas con bcrypt (RNF-02). Adaptador de salida."""

import bcrypt

RONDAS = 12


class BcryptHasher:
    def __init__(self, rondas: int = RONDAS):
        self.rondas = rondas

    def hashear(self, contrasena: str) -> str:
        sal = bcrypt.gensalt(rounds=self.rondas)
        return bcrypt.hashpw(contrasena.encode("utf-8"), sal).decode("ascii")

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            return bcrypt.checkpw(
                contrasena.encode("utf-8"), hash_guardado.encode("ascii")
            )
        except ValueError:
            return False
