"""Compromiso de la cadena de suministro: actualización maliciosa del software de
facturación de un proveedor.

Organizaciones ficticias: Logística Páramo Sur S.A. y el proveedor FacturaPlus.
"""

from app.catalogo_escenarios._base import (
    Nivel,
    NivelAlerta,
    alerta,
    correo,
    documento,
    inject,
    llamada,
    seleccion,
    texto,
)
from app.domain.escenarios import Escenario

NOMBRE = "Actualización maliciosa del software de facturación"


def escenario_cadena_suministro() -> Escenario:
    return Escenario(
        nombre=NOMBRE,
        tipo_codigo="cadena_suministro",
        nivel=Nivel.ALTO,
        descripcion=(
            "El proveedor de software de facturación FacturaPlus (ficticio) "
            "distribuyó una actualización con código malicioso. La empresa ficticia "
            "Logística Páramo Sur S.A. la instaló de forma automática en sus "
            "servidores y estaciones de facturación."
        ),
        roles=["ti", "ciso", "legal", "direccion", "operaciones"],
        injects=[
            inject(
                1,
                "Aviso del proveedor",
                "El proveedor publica un aviso de seguridad sobre la versión 4.2.1 "
                "de su software.",
                0,
                correo(
                    "seguridad@facturaplus.test",
                    "Aviso de seguridad: versión 4.2.1 comprometida",
                    "Detectamos que la actualización 4.2.1, distribuida entre el 2 y "
                    "el 4 de noviembre, contiene un componente no autorizado. "
                    "Recomendamos desconectar los equipos con esa versión mientras "
                    "publicamos la 4.2.2. Seguiremos informando.",
                ),
            ),
            inject(
                2,
                "Conexiones sospechosas",
                "El EDR detecta que el proceso del software de facturación se "
                "conecta a un dominio desconocido.",
                10,
                alerta(
                    "EDR · Servidores",
                    "Proceso firmado contacta dominio no catalogado",
                    "fplus_agent.exe (firma válida de FacturaPlus) en ERP-01 y 9 "
                    "estaciones abrió conexiones HTTPS cada 5 minutos a "
                    "cdn-update-sync.example. Se enviaron 180 MB en 48 horas.",
                    NivelAlerta.ALTA,
                ),
            ),
            inject(
                3,
                "El proveedor no tiene respuestas",
                "Al llamar al proveedor, su soporte no puede confirmar qué datos "
                "pudieron salir.",
                20,
                llamada(
                    "Soporte técnico de FacturaPlus",
                    "Consulta sobre el alcance del incidente",
                    "Todavía estamos investigando con una empresa forense. No "
                    "sabemos qué información accedía el componente. La 4.2.2 sale "
                    "mañana. Por ahora solo podemos recomendar desinstalar.",
                ),
            ),
            inject(
                4,
                "Credenciales del ERP expuestas",
                "El análisis interno confirma que el componente leía el archivo de "
                "configuración con las credenciales del ERP. La facturación está "
                "detenida desde hace 6 horas.",
                35,
                documento(
                    "Equipo interno de respuesta a incidentes",
                    "Informe preliminar de análisis",
                    "El componente malicioso leyó config.ini con el usuario y la "
                    "contraseña de servicio del ERP y la base de clientes. No hay "
                    "evidencia de cifrado ni de movimiento lateral hasta el momento. "
                    "Facturación detenida: 1.150 guías de despacho pendientes.",
                ),
            ),
        ],
        tareas=[
            texto(
                "ti",
                1,
                "El proveedor avisa que la versión 4.2.1 está comprometida. ¿Qué hace "
                "primero?",
                [
                    "Inventariar los equipos con la versión comprometida",
                    "Aislar de la red los equipos afectados",
                    "Suspender las actualizaciones automáticas del proveedor",
                ],
            ),
            seleccion(
                "ciso",
                1,
                "¿Cómo clasifica el evento?",
                [
                    ("Un problema exclusivo del proveedor, sin acción interna", False),
                    (
                        (
                            "Incidente de cadena de suministro: activar el plan de "
                            "respuesta aunque el origen sea un tercero"
                        ),
                        True,
                    ),
                    ("Un falso positivo hasta que el proveedor lo confirme", False),
                ],
            ),
            texto(
                "ti",
                2,
                "El agente se conecta a un dominio desconocido. ¿Qué acciones toma?",
                [
                    "Bloquear el dominio y las direcciones en el firewall y el DNS",
                    "Buscar los indicadores de compromiso en todos los equipos",
                    "Preservar la evidencia antes de desinstalar",
                ],
                dificultad=Nivel.ALTO,
            ),
            seleccion(
                "operaciones",
                2,
                "La facturación está detenida. ¿Qué activa Operaciones?",
                [
                    ("Despachar sin documentos hasta que vuelva el sistema", False),
                    (
                        (
                            "El procedimiento de contingencia de facturación y la "
                            "priorización de despachos críticos"
                        ),
                        True,
                    ),
                    ("Detener todas las operaciones de la empresa", False),
                ],
            ),
            texto(
                "legal",
                3,
                "El proveedor no sabe qué datos salieron. ¿Qué revisa y qué exige "
                "Legal?",
                [
                    "Revisar el contrato y las cláusulas de seguridad del proveedor",
                    "Exigir al proveedor un informe del incidente",
                    "Evaluar la notificación por datos personales de clientes",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=6,
            ),
            texto(
                "ciso",
                4,
                "Las credenciales del ERP fueron leídas. ¿Qué acciones toma?",
                [
                    "Rotar las credenciales del ERP y de las cuentas de servicio",
                    "Revisar los accesos al ERP con esas credenciales",
                    "Restaurar con una versión verificada del software",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
            ),
            texto(
                "direccion",
                4,
                "Hay 1.150 despachos pendientes y clientes esperando. ¿Qué decide la "
                "dirección?",
                [
                    "Priorizar la continuidad de las operaciones críticas",
                    "Comunicar a los clientes los retrasos",
                    "Evaluar el cambio o la auditoría del proveedor",
                ],
            ),
            seleccion(
                "direccion",
                4,
                "Para el futuro, ¿qué exigirá a los proveedores de software?",
                [
                    (
                        (
                            "Evaluación de seguridad de proveedores, notificación de "
                            "incidentes en el contrato y pruebas antes de actualizar"
                        ),
                        True,
                    ),
                    ("Que no publiquen actualizaciones nunca", False),
                    ("Nada: el riesgo es del proveedor", False),
                ],
                dificultad=Nivel.BAJO,
            ),
        ],
    )
