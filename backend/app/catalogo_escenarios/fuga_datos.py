"""Fuga de datos de pacientes por una API expuesta.

Organización ficticia: Clínica Integral Los Alisos.
"""

from app.catalogo_escenarios._base import (
    Nivel,
    NivelAlerta,
    alerta,
    correo,
    documento,
    inject,
    noticia,
    seleccion,
    texto,
)
from app.domain.escenarios import Escenario

NOMBRE = "Fuga de datos de pacientes en el portal de citas"


def escenario_fuga_datos() -> Escenario:
    return Escenario(
        nombre=NOMBRE,
        tipo_codigo="data_breach",
        nivel=Nivel.ALTO,
        descripcion=(
            "Un investigador de seguridad avisa que la API del portal de citas de la "
            "clínica ficticia Clínica Integral Los Alisos devuelve datos de cualquier "
            "paciente cambiando un número en la URL. Hay indicios de descargas "
            "masivas y los datos incluyen información de salud (datos sensibles)."
        ),
        roles=["legal", "ciso", "ti", "relaciones_publicas", "atencion_cliente"],
        injects=[
            inject(
                1,
                "Aviso de un investigador",
                "Llega un correo de un investigador independiente que describe la "
                "vulnerabilidad y adjunta una captura con datos de un paciente.",
                0,
                correo(
                    "investigador.seguridad@proton.example",
                    "Vulnerabilidad crítica en portal de citas (divulgación responsable)",
                    "Hola. En https://citas.losalisos.test/api/pacientes/10234 basta "
                    "cambiar el número para ver nombre, cédula, teléfono, "
                    "diagnóstico y próxima cita de cualquier paciente, sin iniciar "
                    "sesión. No he descargado datos. Les doy 15 días antes de "
                    "publicar los detalles.",
                ),
            ),
            inject(
                2,
                "Descargas masivas",
                "Los registros muestran que una IP externa recorrió la API de forma "
                "secuencial durante tres noches.",
                15,
                alerta(
                    "WAF · Portal de citas",
                    "Enumeración de identificadores en /api/pacientes",
                    "IP 203.0.113.77 realizó 85.412 solicitudes GET /api/pacientes/"
                    "{id} entre el 3 y el 5 de noviembre (ids 1 a 85.412), todas con "
                    "respuesta 200. Volumen transferido: 412 MB.",
                    NivelAlerta.CRITICA,
                ),
            ),
            inject(
                3,
                "La noticia sale a la luz",
                "Un medio digital publica que datos de pacientes se venden en un foro.",
                30,
                noticia(
                    "Portal Noticias Hoy (ficticio)",
                    "Ofrecen en un foro datos de 85 mil pacientes de una clínica de Quito",
                    "Un usuario de un foro clandestino ofrece por USD 3.000 una base "
                    "con nombres, cédulas y diagnósticos que atribuye a la Clínica "
                    "Integral Los Alisos. La clínica no ha emitido un pronunciamiento.",
                ),
            ),
            inject(
                4,
                "Requerimiento de la autoridad",
                "Llega un oficio de la Superintendencia de Protección de Datos "
                "Personales pidiendo información sobre el incidente.",
                45,
                documento(
                    "Superintendencia de Protección de Datos Personales",
                    "Oficio de requerimiento de información",
                    "Se solicita informar en el término legal: naturaleza de la "
                    "vulneración, categorías y número aproximado de titulares "
                    "afectados, medidas adoptadas y comunicación a los titulares. "
                    "(Documento ficticio para el ejercicio.)",
                ),
            ),
        ],
        tareas=[
            texto(
                "ti",
                1,
                "¿Qué hace con la API vulnerable en la primera hora?",
                [
                    "Deshabilitar o restringir el endpoint vulnerable",
                    "Exigir autenticación y autorización por paciente",
                    "Preservar los registros de acceso",
                ],
            ),
            seleccion(
                "ciso",
                1,
                "¿Cómo responde al investigador que reportó la vulnerabilidad?",
                [
                    ("Amenazarlo con una demanda para que no publique", False),
                    (
                        (
                            "Agradecer, confirmar la recepción, coordinar plazos y "
                            "pedirle que no difunda detalles"
                        ),
                        True,
                    ),
                    ("Ignorar el correo hasta tener el informe completo", False),
                ],
            ),
            texto(
                "ciso",
                2,
                "Hay 85.412 solicitudes desde una IP externa. ¿Cómo determina el "
                "alcance de la fuga?",
                [
                    "Identificar qué registros y campos fueron descargados",
                    "Determinar el número de titulares afectados",
                    "Clasificar los datos de salud como datos sensibles",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
            ),
            texto(
                "legal",
                2,
                "Se confirmó la fuga de datos de salud. ¿Qué obligaciones tiene la "
                "clínica según la Ley Orgánica de Protección de Datos Personales?",
                [
                    "Notificar la vulneración a la autoridad de protección de datos",
                    "Comunicar a los titulares afectados",
                    "Documentar el incidente y las medidas adoptadas",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=7,
            ),
            texto(
                "relaciones_publicas",
                3,
                "El medio ya publicó la noticia. Redacte los puntos clave del "
                "comunicado oficial.",
                [
                    "Reconocer el incidente con transparencia",
                    "Explicar las medidas tomadas para proteger a los pacientes",
                    "Indicar un canal de atención para los afectados",
                ],
                minutos=6,
            ),
            seleccion(
                "atencion_cliente",
                3,
                "Un paciente llama alterado preguntando si sus datos fueron robados. "
                "¿Qué le responde?",
                [
                    ("Que no se preocupe porque no pasó nada", False),
                    (
                        (
                            "Que la clínica investiga el incidente, que recibirá "
                            "información oficial y cómo protegerse ante fraudes"
                        ),
                        True,
                    ),
                    ("Que llame a la Fiscalía", False),
                    ("Le confirma si su registro está en la base filtrada", False),
                ],
                dificultad=Nivel.BAJO,
            ),
            texto(
                "legal",
                4,
                "¿Qué información entrega a la Superintendencia en respuesta al oficio?",
                [
                    "Naturaleza de la vulneración y fecha de detección",
                    "Número de titulares y categorías de datos afectados",
                    "Medidas de contención y comunicación a los titulares",
                ],
                dificultad=Nivel.ALTO,
            ),
            seleccion(
                "ti",
                4,
                "Para el informe de lecciones aprendidas, ¿cuál fue la causa raíz?",
                [
                    ("Un ataque de fuerza bruta a contraseñas", False),
                    (
                        (
                            "Control de acceso roto: la API no verificaba que el "
                            "paciente fuera dueño del registro (IDOR)"
                        ),
                        True,
                    ),
                    ("Un ransomware en el servidor de base de datos", False),
                ],
            ),
        ],
    )
