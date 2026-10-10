"""Casos de uso de la biblioteca de escenarios (PB-03 y PB-04).

Coordina dominio y puertos. No conoce HTTP ni SQLAlchemy.
"""

from uuid import UUID

from app.domain.escenarios import Escenario, EstadoEscenario, ReglaEscenarioError
from app.ports.escenario_repository import (
    CatalogoRepository,
    EscenarioRepository,
    FiltroBanco,
    FiltroEscenarios,
    TareaDelBanco,
)


class EscenarioNoEncontrado(LookupError):
    pass


class ServicioEscenarios:
    def __init__(self, repo: EscenarioRepository, catalogo: CatalogoRepository):
        self.repo = repo
        self.catalogo = catalogo

    # --- PB-03: administración (solo Administrador) -------------------------

    def crear(self, escenario: Escenario) -> Escenario:
        self._validar_catalogos(escenario)
        escenario.estado = EstadoEscenario.BORRADOR
        escenario.es_base = True
        escenario.validar_consistencia()
        return self.repo.guardar(escenario)

    def actualizar(self, escenario_id: UUID, nuevo: Escenario) -> Escenario:
        actual = self._obtener_o_error(escenario_id)
        self._validar_catalogos(nuevo)
        actual.reemplazar_contenido(nuevo)
        return self.repo.guardar(actual)

    def publicar(self, escenario_id: UUID) -> Escenario:
        escenario = self._obtener_o_error(escenario_id)
        escenario.publicar()
        return self.repo.guardar(escenario)

    def archivar(self, escenario_id: UUID) -> Escenario:
        escenario = self._obtener_o_error(escenario_id)
        escenario.archivar()
        return self.repo.guardar(escenario)

    # --- PB-04: consulta de la biblioteca ------------------------------------

    def listar(
        self, filtro: FiltroEscenarios, puede_gestionar: bool
    ) -> list[Escenario]:
        if not puede_gestionar:
            # El moderador solo ve escenarios publicados.
            filtro.estados = [EstadoEscenario.PUBLICADO]
        elif not filtro.estados:
            filtro.estados = [EstadoEscenario.BORRADOR, EstadoEscenario.PUBLICADO]
        return self.repo.listar(filtro)

    def obtener(self, escenario_id: UUID, puede_gestionar: bool) -> Escenario:
        escenario = self._obtener_o_error(escenario_id)
        if not puede_gestionar and escenario.estado != EstadoEscenario.PUBLICADO:
            raise EscenarioNoEncontrado(str(escenario_id))
        return escenario

    def banco_de_preguntas(
        self, filtro: FiltroBanco, puede_gestionar: bool
    ) -> list[TareaDelBanco]:
        if not puede_gestionar:
            filtro.solo_publicados = True
        return self.repo.buscar_tareas(filtro)

    # --- apoyo ----------------------------------------------------------------

    def _obtener_o_error(self, escenario_id: UUID) -> Escenario:
        escenario = self.repo.obtener(escenario_id)
        if escenario is None:
            raise EscenarioNoEncontrado(str(escenario_id))
        return escenario

    def _validar_catalogos(self, escenario: Escenario) -> None:
        errores: list[str] = []
        tipos = {t.codigo for t in self.catalogo.tipos_escenario()}
        if escenario.tipo_codigo not in tipos:
            errores.append(f"Tipo de escenario desconocido: {escenario.tipo_codigo}")
        roles = {r.codigo for r in self.catalogo.roles_ejercicio()}
        desconocidos = sorted(set(escenario.roles) - roles)
        if desconocidos:
            errores.append("Roles desconocidos: " + ", ".join(desconocidos))
        if errores:
            raise ReglaEscenarioError(errores)
