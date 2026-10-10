"""Carga un escenario de ejemplo publicado (banco de preguntas inicial).

Uso: docker compose exec backend python -m app.seed_escenarios

Es idempotente: si el escenario ya existe, no hace nada. Todo el contenido es
ficticio, sin datos reales de clientes de NODOVIP.
"""

from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.database import get_engine
from app.adapters.outbound.persistence.repositorio_escenarios import (
    SqlCatalogoRepository,
    SqlEscenarioRepository,
)
from app.application.escenarios import ServicioEscenarios
from app.domain.escenarios import Escenario, Inject, Nivel, Tarea
from app.ports.escenario_repository import FiltroEscenarios

NOMBRE = "Ransomware en servidores de archivos"


def escenario_ransomware() -> Escenario:
    return Escenario(
        nombre=NOMBRE,
        tipo_codigo="ransomware",
        nivel=Nivel.ALTO,
        descripcion=(
            "Un lunes a las 07:40 el equipo de TI detecta que los servidores de "
            "archivos de la empresa ficticia Comercial Andina S.A. muestran archivos "
            "con extensión .lock y una nota de rescate que exige 40 BTC en 72 horas."
        ),
        roles=["ciso", "comunicaciones", "director_ejecutivo", "legal", "ti"],
        injects=[
            Inject(
                orden=1,
                titulo="Detección inicial",
                descripcion=(
                    "Mesa de ayuda recibe 25 llamadas: nadie puede abrir documentos "
                    "compartidos y aparece una nota de rescate en cada carpeta."
                ),
                minuto_sugerido=0,
            ),
            Inject(
                orden=2,
                titulo="Propagación a respaldos",
                descripcion=(
                    "TI confirma que el servidor de respaldos en la red interna "
                    "también fue cifrado. Solo queda una copia fuera de línea de "
                    "hace 9 días."
                ),
                minuto_sugerido=15,
            ),
            Inject(
                orden=3,
                titulo="Amenaza de publicación",
                descripcion=(
                    "Los atacantes envían una muestra de 200 registros de clientes y "
                    "amenazan con publicar toda la base si no se paga en 24 horas."
                ),
                minuto_sugerido=30,
            ),
            Inject(
                orden=4,
                titulo="Consulta de la prensa",
                descripcion=(
                    "Un periodista llama a la central preguntando por un posible "
                    "ataque informático que afecta a los clientes."
                ),
                minuto_sugerido=45,
            ),
        ],
        tareas=[
            Tarea(
                enunciado=(
                    "¿Cuáles son las tres primeras acciones técnicas para contener "
                    "la propagación del ransomware?"
                ),
                rol_codigo="ti",
                dificultad=Nivel.MEDIO,
                criterios=[
                    "Aislar los equipos y segmentos afectados de la red",
                    "Preservar evidencia antes de restaurar",
                    "Verificar la integridad de la copia fuera de línea",
                ],
                puntaje_maximo=10,
                tiempo_limite_segundos=300,
            ),
            Tarea(
                enunciado=(
                    "Clasifique la severidad del incidente y explique a quién "
                    "escala la decisión y en qué plazo."
                ),
                rol_codigo="ciso",
                dificultad=Nivel.MEDIO,
                criterios=[
                    "Clasifica el incidente como crítico",
                    "Activa el plan de respuesta a incidentes",
                    "Escala a la alta dirección de inmediato",
                ],
                puntaje_maximo=10,
                tiempo_limite_segundos=300,
            ),
            Tarea(
                enunciado=(
                    "¿Qué obligaciones de notificación tiene la empresa ante la "
                    "posible exposición de datos personales de clientes?"
                ),
                rol_codigo="legal",
                dificultad=Nivel.ALTO,
                criterios=[
                    (
                        "Identifica la obligación de notificar a la autoridad de "
                        "protección de datos"
                    ),
                    "Considera la notificación a los titulares afectados",
                    "Documenta plazos y evidencia del incidente",
                ],
                puntaje_maximo=15,
                tiempo_limite_segundos=420,
            ),
            Tarea(
                enunciado=(
                    "Los atacantes exigen el pago del rescate. ¿Qué decisión toma y "
                    "qué factores considera?"
                ),
                rol_codigo="director_ejecutivo",
                dificultad=Nivel.ALTO,
                criterios=[
                    "Consulta a Legal, CISO y asesores antes de decidir",
                    "Considera que pagar no garantiza recuperar los datos",
                    "Prioriza la continuidad del negocio y la recuperación",
                ],
                puntaje_maximo=15,
                tiempo_limite_segundos=420,
            ),
            Tarea(
                enunciado=(
                    "Redacte la respuesta inicial al periodista que pregunta por el "
                    "ataque."
                ),
                rol_codigo="comunicaciones",
                dificultad=Nivel.BAJO,
                criterios=[
                    "No confirma datos no verificados",
                    "Usa un mensaje coordinado con Legal y Dirección",
                    "Indica que habrá información oficial posterior",
                ],
                puntaje_maximo=10,
                tiempo_limite_segundos=300,
            ),
        ],
    )


def main() -> None:
    with Session(get_engine()) as session:
        servicio = ServicioEscenarios(
            SqlEscenarioRepository(session), SqlCatalogoRepository(session)
        )
        existentes = servicio.listar(
            FiltroEscenarios(texto=NOMBRE), puede_gestionar=True
        )
        if any(e.nombre == NOMBRE for e in existentes):
            print(f"Ya existe: {NOMBRE}")
            return
        escenario = servicio.crear(escenario_ransomware())
        servicio.publicar(escenario.id)
        print(f"Escenario publicado: {NOMBRE} ({escenario.id})")


if __name__ == "__main__":
    main()
