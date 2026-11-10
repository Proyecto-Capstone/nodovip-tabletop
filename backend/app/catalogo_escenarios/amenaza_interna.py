"""Amenaza interna: analista comercial que renuncia y se lleva la cartera.

Organización ficticia: Distribuidora Ventisquero S.A.
"""

from app.catalogo_escenarios._base import (
    Nivel,
    NivelAlerta,
    alerta,
    documento,
    inject,
    llamada,
    seleccion,
    texto,
)
from app.domain.escenarios import Escenario

NOMBRE = "Amenaza interna: extracción de la cartera de clientes"


def escenario_amenaza_interna() -> Escenario:
    return Escenario(
        nombre=NOMBRE,
        tipo_codigo="insider_threat",
        nivel=Nivel.MEDIO,
        descripcion=(
            "Un analista comercial con acceso al CRM de la empresa ficticia "
            "Distribuidora Ventisquero S.A. presenta su renuncia para irse a la "
            "competencia. En los días previos copió información de clientes y "
            "precios a medios personales."
        ),
        roles=["ciso", "ti", "rrhh", "legal", "direccion"],
        injects=[
            inject(
                1,
                "Alerta de copia a USB",
                "La herramienta de prevención de fuga de datos (DLP) reporta una "
                "copia grande a un dispositivo USB personal.",
                0,
                alerta(
                    "DLP · Estaciones de trabajo",
                    "Copia masiva a dispositivo extraíble no autorizado",
                    "Equipo PC-VENT-23 (usuario jtorres). 3,2 GB copiados a una "
                    "memoria USB 'SanDisk 64GB' a las 19:42. Archivos: "
                    "clientes_2026.xlsx, lista_precios_mayoristas.pdf y 412 "
                    "cotizaciones.",
                    NivelAlerta.MEDIA,
                ),
            ),
            inject(
                2,
                "Carta de renuncia",
                "Al día siguiente el mismo analista entrega su renuncia, efectiva en "
                "48 horas.",
                10,
                documento(
                    "Recursos Humanos",
                    "Renuncia voluntaria — J. Torres, analista comercial",
                    "Por motivos personales presento mi renuncia al cargo de analista "
                    "comercial, efectiva a partir del jueves. Agradezco la "
                    "oportunidad. (En su perfil profesional ya figura un nuevo cargo "
                    "en una distribuidora de la competencia.)",
                ),
            ),
            inject(
                3,
                "Accesos fuera de horario",
                "Se detectan exportaciones del CRM a las 23:00 desde una VPN, con la "
                "cuenta del analista.",
                20,
                alerta(
                    "CRM · Registro de auditoría",
                    "Exportación masiva fuera de horario",
                    "Usuario jtorres exportó 'Todos los clientes activos' (5.870 "
                    "registros con contactos y volúmenes de compra) a las 23:07 y "
                    "23:15 desde la VPN corporativa.",
                    NivelAlerta.ALTA,
                ),
            ),
            inject(
                4,
                "Un cliente avisa",
                "Un cliente mayorista llama sorprendido porque la competencia le "
                "ofreció exactamente sus precios con un descuento.",
                35,
                llamada(
                    "Gerente de compras de un cliente mayorista",
                    "Oferta de la competencia con nuestros precios",
                    "Me llamó Distribuidora del Norte con mi historial de compras y "
                    "un 7 % menos en cada producto. ¿Ustedes les pasaron mi "
                    "información? Esto no me parece serio.",
                ),
            ),
        ],
        tareas=[
            texto(
                "ciso",
                1,
                "La DLP reporta la copia a USB. ¿Cómo investiga sin alertar al "
                "empleado?",
                [
                    "Preservar la evidencia y los registros de la DLP",
                    "Revisar los accesos recientes del usuario de forma discreta",
                    "Coordinar con Recursos Humanos y Legal antes de actuar",
                ],
                dificultad=Nivel.ALTO,
            ),
            seleccion(
                "ti",
                1,
                "¿Qué acción técnica corresponde mientras se investiga?",
                [
                    ("Borrar la cuenta del usuario de inmediato", False),
                    (
                        (
                            "Bloquear los dispositivos USB en su equipo y aumentar el "
                            "monitoreo, sin borrar evidencia"
                        ),
                        True,
                    ),
                    ("Formatear su computador", False),
                ],
            ),
            texto(
                "rrhh",
                2,
                "El analista renunció y se va en 48 horas. ¿Cómo maneja su salida?",
                [
                    "Coordinar la revocación de accesos con TI el último día",
                    "Recuperar los equipos y activos de la empresa",
                    "Recordar el acuerdo de confidencialidad en la entrevista de salida",
                ],
            ),
            seleccion(
                "direccion",
                2,
                "¿Cuándo deben revocarse los accesos del analista?",
                [
                    ("Al final del mes, con la liquidación", False),
                    (
                        (
                            "De inmediato para la información crítica, coordinado con "
                            "RRHH y Legal"
                        ),
                        True,
                    ),
                    ("No hace falta: ya presentó la renuncia", False),
                ],
                dificultad=Nivel.BAJO,
            ),
            texto(
                "ti",
                3,
                "Hubo exportaciones del CRM a las 23:00 por VPN. ¿Qué hace?",
                [
                    "Revocar el acceso a la VPN y al CRM",
                    "Conservar los registros de auditoría del CRM",
                    "Revisar si hay otras cuentas con exportaciones similares",
                ],
            ),
            texto(
                "legal",
                3,
                "¿Qué acciones legales evalúa la empresa?",
                [
                    "Revisar el acuerdo de confidencialidad firmado",
                    "Mantener la cadena de custodia de la evidencia",
                    "Evaluar la protección de los datos personales de los contactos",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=6,
            ),
            texto(
                "direccion",
                4,
                "Un cliente mayorista está molesto. ¿Qué decide la dirección?",
                [
                    "Contactar personalmente al cliente con transparencia",
                    "Proteger la relación comercial con los clientes clave",
                    "Aprobar las acciones legales recomendadas",
                ],
            ),
            seleccion(
                "ciso",
                4,
                "¿Qué control habría reducido el impacto de este incidente?",
                [
                    (
                        (
                            "Mínimo privilegio en el CRM y alertas de exportaciones "
                            "masivas"
                        ),
                        True,
                    ),
                    ("Prohibir las renuncias con poco aviso", False),
                    (
                        "Desactivar todos los puertos USB de la empresa sin excepción",
                        False,
                    ),
                ],
            ),
        ],
    )
