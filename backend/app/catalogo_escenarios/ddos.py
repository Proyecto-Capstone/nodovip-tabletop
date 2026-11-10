"""DDoS con extorsión contra la banca en línea en día de pago.

Organización ficticia: Cooperativa de Ahorro y Crédito Nevado Plata.
"""

from app.catalogo_escenarios._base import (
    Nivel,
    NivelAlerta,
    alerta,
    correo,
    inject,
    mensaje,
    noticia,
    seleccion,
    texto,
)
from app.domain.escenarios import Escenario

NOMBRE = "Caída de la banca en línea por DDoS en día de pago"


def escenario_ddos() -> Escenario:
    return Escenario(
        nombre=NOMBRE,
        tipo_codigo="ddos",
        nivel=Nivel.MEDIO,
        descripcion=(
            "El día 15, fecha de pago de sueldos, la banca en línea y la app de la "
            "cooperativa ficticia Nevado Plata dejan de responder por un ataque de "
            "denegación de servicio distribuido. Un grupo extorsivo exige un pago "
            "para detenerlo."
        ),
        roles=[
            "ti",
            "operaciones",
            "atencion_cliente",
            "comunicaciones",
            "director_ejecutivo",
        ],
        injects=[
            inject(
                1,
                "La banca en línea no responde",
                "A las 08:05 el monitoreo reporta tiempos de respuesta de 30 segundos "
                "y luego caída total de la banca en línea y la app móvil.",
                0,
                alerta(
                    "Monitoreo de red · Perímetro",
                    "Tráfico anómalo hacia banca.nevadoplata.test",
                    "Pico de 38 Gbps (normal: 1,2 Gbps). 2,1 millones de solicitudes "
                    "HTTPS por segundo desde 14.000 IP de 60 países. Disponibilidad "
                    "del portal: 3 %.",
                    NivelAlerta.CRITICA,
                ),
            ),
            inject(
                2,
                "Correo de extorsión",
                "Llega un mensaje que se atribuye el ataque y pide un pago en "
                "criptomonedas.",
                10,
                correo(
                    "phantom.squad@protonmail.example",
                    "Esto es solo una demostración",
                    "Su banca en línea está fuera de servicio. Paguen 2 BTC antes de "
                    "las 14:00 o el ataque se triplicará y seguirá todo el mes. No "
                    "intenten mitigarlo: tenemos más capacidad que su proveedor.",
                ),
            ),
            inject(
                3,
                "Colapso del centro de llamadas",
                "Los socios no pueden cobrar su sueldo y saturan el centro de llamadas.",
                20,
                mensaje(
                    "Supervisora del centro de llamadas (chat interno)",
                    "No damos abasto",
                    "Tenemos 340 llamadas en espera y la espera promedio es de 25 "
                    "minutos. La gente está molesta porque hoy es día de pago. ¿Qué "
                    "les decimos? ¿Hay alguna alternativa para retirar dinero?",
                ),
            ),
            inject(
                4,
                "Tendencia en redes sociales",
                "El hashtag sobre la caída se vuelve tendencia y aparecen rumores de "
                "que la cooperativa está quebrada.",
                35,
                noticia(
                    "Red social · Tendencias Ecuador (ficticio)",
                    "#NevadoPlataCaído es tendencia",
                    "'¿Alguien sabe si Nevado Plata quebró? No puedo sacar mi plata' "
                    "(4.200 reacciones). Varios usuarios piden retirar sus ahorros en "
                    "las agencias.",
                ),
            ),
        ],
        tareas=[
            texto(
                "ti",
                1,
                "¿Qué acciones técnicas toma para mitigar el ataque?",
                [
                    "Activar la mitigación DDoS con el proveedor de internet o la CDN",
                    "Aplicar limitación de tasa y filtrado de tráfico en el WAF",
                    "Monitorear la disponibilidad y escalar al proveedor",
                ],
            ),
            seleccion(
                "operaciones",
                1,
                "La banca en línea está caída en día de pago. ¿Qué activa primero?",
                [
                    ("Cerrar las agencias hasta que vuelva el sistema", False),
                    (
                        (
                            "El plan de continuidad: canales alternos como agencias con "
                            "horario extendido y cajeros automáticos"
                        ),
                        True,
                    ),
                    ("Postergar el pago de sueldos al día siguiente", False),
                ],
            ),
            seleccion(
                "director_ejecutivo",
                2,
                "El grupo exige 2 BTC para detener el ataque. ¿Cuál es la postura?",
                [
                    ("Pagar para recuperar el servicio cuanto antes", False),
                    (
                        (
                            "No pagar, reforzar la mitigación y denunciar ante las "
                            "autoridades"
                        ),
                        True,
                    ),
                    ("Negociar una rebaja con los atacantes", False),
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
            ),
            texto(
                "ti",
                2,
                "¿Qué evidencia conserva del ataque y del correo de extorsión?",
                [
                    "Conservar los registros de tráfico y del WAF",
                    "Guardar el correo de extorsión con sus cabeceras",
                    "Compartir los indicadores con el CSIRT nacional",
                ],
            ),
            texto(
                "atencion_cliente",
                3,
                "Escriba el guion breve que usarán los agentes del centro de llamadas.",
                [
                    "Informar que los fondos están seguros",
                    "Indicar los canales alternos para retirar dinero",
                    "No dar detalles técnicos del ataque",
                ],
                dificultad=Nivel.BAJO,
            ),
            texto(
                "comunicaciones",
                4,
                "Circula el rumor de que la cooperativa quebró. ¿Qué comunica y por "
                "qué canales?",
                [
                    "Desmentir el rumor y aclarar que los fondos están seguros",
                    "Publicar en los canales oficiales y redes sociales",
                    "Actualizar la información periódicamente",
                ],
                minutos=6,
            ),
            seleccion(
                "director_ejecutivo",
                4,
                "Para el directorio, ¿qué decisión de mejora prioriza después del "
                "incidente?",
                [
                    (
                        (
                            "Contratar protección DDoS permanente y probar el plan de "
                            "continuidad"
                        ),
                        True,
                    ),
                    ("Desactivar la banca en línea en días de pago", False),
                    ("Cambiar el nombre de la app para evitar ataques", False),
                ],
            ),
        ],
    )
