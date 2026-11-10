"""Ransomware en servidores de archivos (empresa ficticia Comercial Andina S.A.)."""

from app.catalogo_escenarios._base import (
    Nivel,
    NivelAlerta,
    alerta,
    correo,
    inject,
    llamada,
    mensaje,
    seleccion,
    texto,
)
from app.domain.escenarios import Escenario

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
            inject(
                1,
                "Detección inicial",
                "Mesa de ayuda recibe 25 llamadas: nadie puede abrir documentos "
                "compartidos y aparece una nota de rescate en cada carpeta.",
                0,
                alerta(
                    "EDR corporativo · FS-01",
                    "Cifrado masivo de archivos detectado",
                    "Proceso svc_update.exe renombró 18.412 archivos a .lock en 6 "
                    "minutos en la carpeta compartida de FS-01. Se creó LEEME.txt en "
                    "cada carpeta. Host origen: PC-CONT-07 (usuario mlopez).",
                    NivelAlerta.CRITICA,
                ),
            ),
            inject(
                2,
                "Propagación a respaldos",
                "TI confirma que el servidor de respaldos en la red interna también "
                "fue cifrado. Solo queda una copia fuera de línea de hace 9 días.",
                15,
                mensaje(
                    "Jefe de infraestructura (chat interno)",
                    "Respaldos comprometidos",
                    "Malas noticias: BKP-02 también está cifrado, el catálogo de "
                    "respaldos no abre. Lo único limpio es la cinta fuera de sitio "
                    "del día 31. ¿Restauramos desde ahí o esperamos a forense?",
                ),
            ),
            inject(
                3,
                "Amenaza de publicación",
                "Los atacantes envían una muestra de 200 registros de clientes y "
                "amenazan con publicar toda la base si no se paga en 24 horas.",
                30,
                correo(
                    "lockbit-support@onionmail.example",
                    "Prueba de los datos de sus clientes — 24 horas",
                    "Adjuntamos 200 registros de su base de clientes (nombre, cédula, "
                    "correo, saldo). Tenemos 1,8 millones más. Si no recibimos el "
                    "pago en 24 horas publicaremos todo en nuestro blog y avisaremos "
                    "a la prensa.",
                ),
            ),
            inject(
                4,
                "Consulta de la prensa",
                "Un periodista llama a la central preguntando por un posible ataque "
                "informático que afecta a los clientes.",
                45,
                llamada(
                    "Periodista de Diario El Observador (ficticio)",
                    "Consulta sobre un ataque informático",
                    "Buenos días, le llamo de Diario El Observador. Varios clientes "
                    "nos escriben que no pueden usar sus servicios y en un foro dicen "
                    "que Comercial Andina fue hackeada. ¿Pueden confirmarlo? "
                    "Publicamos a las 18:00.",
                ),
            ),
        ],
        tareas=[
            texto(
                "ti",
                1,
                "¿Cuáles son las tres primeras acciones técnicas para contener la "
                "propagación del ransomware?",
                [
                    "Aislar los equipos y segmentos afectados de la red",
                    "Preservar evidencia antes de restaurar",
                    "Verificar la integridad de la copia fuera de línea",
                ],
            ),
            texto(
                "ciso",
                1,
                "Clasifique la severidad del incidente y explique a quién escala la "
                "decisión y en qué plazo.",
                [
                    "Clasifica el incidente como crítico",
                    "Activa el plan de respuesta a incidentes",
                    "Escala a la alta dirección de inmediato",
                ],
            ),
            seleccion(
                "ti",
                2,
                "Los respaldos en línea están cifrados y solo queda la cinta de hace 9 "
                "días. ¿Qué hace antes de restaurar?",
                [
                    ("Restaurar de inmediato sobre los mismos servidores", False),
                    (
                        (
                            "Verificar que la cinta esté limpia y restaurar en un "
                            "entorno aislado y reconstruido"
                        ),
                        True,
                    ),
                    (
                        "Esperar a que el atacante entregue la llave de descifrado",
                        False,
                    ),
                    ("Formatear todos los equipos sin preservar evidencia", False),
                ],
            ),
            seleccion(
                "ciso",
                2,
                "¿Qué debe quedar documentado desde ahora para el análisis forense?",
                [
                    ("Solo la hora en que se pagó el rescate", False),
                    (
                        (
                            "Línea de tiempo, equipos afectados, indicadores de "
                            "compromiso y cadena de custodia de la evidencia"
                        ),
                        True,
                    ),
                    ("Nada: primero hay que recuperar el servicio", False),
                ],
                dificultad=Nivel.ALTO,
            ),
            texto(
                "director_ejecutivo",
                3,
                "Los atacantes exigen el pago del rescate y amenazan con publicar los "
                "datos. ¿Qué decisión toma y qué factores considera?",
                [
                    "Consulta a Legal, CISO y asesores antes de decidir",
                    "Considera que pagar no garantiza recuperar los datos",
                    "Prioriza la continuidad del negocio y la recuperación",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=7,
            ),
            texto(
                "legal",
                3,
                "¿Qué obligaciones de notificación tiene la empresa ante la posible "
                "exposición de datos personales de clientes?",
                [
                    "Identifica la obligación de notificar a la autoridad de protección de datos",
                    "Considera la notificación a los titulares afectados",
                    "Documenta plazos y evidencia del incidente",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=7,
            ),
            texto(
                "comunicaciones",
                4,
                "Redacte la respuesta inicial al periodista que pregunta por el ataque.",
                [
                    "No confirma datos no verificados",
                    "Usa un mensaje coordinado con Legal y Dirección",
                    "Indica que habrá información oficial posterior",
                ],
                dificultad=Nivel.BAJO,
            ),
            seleccion(
                "legal",
                4,
                "El periodista publicará a las 18:00. ¿Qué revisa Legal antes de que "
                "Comunicaciones responda?",
                [
                    ("Que el mensaje no admita responsabilidades no verificadas", True),
                    ("Que se incluyan los nombres de los clientes afectados", False),
                    (
                        "Que se culpe públicamente al empleado del equipo infectado",
                        False,
                    ),
                ],
                dificultad=Nivel.BAJO,
            ),
        ],
    )
