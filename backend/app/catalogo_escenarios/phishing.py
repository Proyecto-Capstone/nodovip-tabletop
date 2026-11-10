"""Phishing dirigido al gerente financiero y fraude de transferencia (BEC).

Organización ficticia: Seguros Cordillera Azul S.A.
"""

from app.catalogo_escenarios._base import (
    Nivel,
    NivelAlerta,
    alerta,
    correo,
    inject,
    mensaje,
    seleccion,
    texto,
)
from app.domain.escenarios import Escenario

NOMBRE = "Phishing al gerente financiero y fraude de transferencia"


def escenario_phishing() -> Escenario:
    return Escenario(
        nombre=NOMBRE,
        tipo_codigo="phishing_dirigido",
        nivel=Nivel.MEDIO,
        descripcion=(
            "El gerente financiero de la aseguradora ficticia Seguros Cordillera Azul "
            "S.A. ingresó su contraseña en una página falsa de inicio de sesión. Con "
            "su cuenta, el atacante crea reglas de reenvío y solicita una "
            "transferencia urgente a un proveedor que no existe (Business Email "
            "Compromise)."
        ),
        roles=["ciso", "ti", "director_ejecutivo", "legal", "rrhh"],
        injects=[
            inject(
                1,
                "Correo de verificación de cuenta",
                "El gerente financiero reporta a la mesa de ayuda que ayer ingresó su "
                "usuario y contraseña en un enlace para 'verificar su cuenta' y que la "
                "página quedó en blanco.",
                0,
                correo(
                    "seguridad@m1crosoft-soporte.example",
                    "Acción requerida: su cuenta será bloqueada en 24 horas",
                    "Estimado usuario: detectamos actividad inusual. Para evitar el "
                    "bloqueo de su buzón, verifique su identidad en el siguiente "
                    "enlace: https://login-verificacion.example/cordillera. Equipo de "
                    "Seguridad.",
                ),
            ),
            inject(
                2,
                "Accesos desde otro país",
                "El SIEM correlaciona accesos imposibles y una regla de reenvío creada "
                "en el buzón del gerente durante la madrugada.",
                12,
                alerta(
                    "SIEM · Identidad",
                    "Viaje imposible y regla de reenvío sospechosa",
                    "Usuario: gerente.financiero@cordilleraazul.test. 02:14 inicio de "
                    "sesión desde Quito; 02:26 desde Lagos (Nigeria). 02:31 regla "
                    "'Sincronizar' reenvía correos con 'pago', 'factura' o "
                    "'transferencia' a cobros.externos@mailbox.example.",
                    NivelAlerta.ALTA,
                ),
            ),
            inject(
                3,
                "Pedido de transferencia urgente",
                "Tesorería recibió desde la cuenta del gerente una orden de pago "
                "urgente y confidencial a un proveedor nuevo.",
                25,
                mensaje(
                    "Analista de Tesorería (chat interno)",
                    "¿Proceso este pago?",
                    "Me llegó un correo del gerente pidiendo transferir hoy USD 48.500 "
                    "a 'Consultores Integrales del Pacífico' por un contrato "
                    "confidencial. Dice que no lo llame porque está en reunión con "
                    "la junta. Ya lo cargué en la banca en línea, ¿lo apruebo?",
                ),
            ),
            inject(
                4,
                "El pago ya salió",
                "Se descubre que una transferencia anterior de USD 31.200 ya fue "
                "ejecutada ayer con el mismo procedimiento.",
                40,
                correo(
                    "cobranzas@talleres-reunidos.test",
                    "Factura 0045 vencida — segundo aviso",
                    "Buenos días. Les recordamos que la factura 0045 por USD 31.200 "
                    "sigue impaga. Nos sorprende su correo indicando un cambio de "
                    "cuenta bancaria: nosotros no hemos cambiado de banco. Talleres "
                    "Reunidos (ficticio).",
                ),
            ),
        ],
        tareas=[
            texto(
                "ti",
                1,
                "El gerente entregó su contraseña. ¿Qué acciones toma de inmediato "
                "sobre su cuenta?",
                [
                    "Restablecer la contraseña y revocar las sesiones activas",
                    "Activar o verificar la autenticación multifactor",
                    "Revisar los registros de acceso de la cuenta",
                ],
            ),
            seleccion(
                "ciso",
                1,
                "Con la información disponible, ¿cómo clasifica el evento?",
                [
                    ("Falso positivo: el usuario no recuerda bien", False),
                    (
                        (
                            "Incidente de compromiso de credenciales: contener la cuenta "
                            "y buscar otros afectados por la misma campaña"
                        ),
                        True,
                    ),
                    ("Solo un problema de capacitación, sin acciones técnicas", False),
                ],
            ),
            texto(
                "ti",
                2,
                "El SIEM muestra una regla de reenvío y accesos desde Nigeria. ¿Qué "
                "hace con la regla y con la evidencia?",
                [
                    "Eliminar la regla de reenvío después de documentarla",
                    "Bloquear la dirección externa de reenvío",
                    "Preservar los registros del buzón como evidencia",
                ],
                dificultad=Nivel.ALTO,
            ),
            texto(
                "rrhh",
                2,
                "¿Cómo acompaña al gerente que cayó en el engaño y qué hace para que "
                "no le pase a otros?",
                [
                    "Evitar represalias y apoyar al colaborador",
                    "Reforzar la capacitación en phishing para todo el personal",
                    "Documentar el caso para el plan de concienciación",
                ],
                dificultad=Nivel.BAJO,
            ),
            seleccion(
                "director_ejecutivo",
                3,
                "Tesorería pregunta si aprueba la transferencia de USD 48.500. ¿Qué "
                "instruye?",
                [
                    ("Aprobarla: el pedido viene del correo del gerente", False),
                    (
                        (
                            "Detenerla y confirmar por un canal distinto (llamada al "
                            "número conocido del gerente)"
                        ),
                        True,
                    ),
                    ("Aprobarla por la mitad del monto mientras se aclara", False),
                ],
                dificultad=Nivel.BAJO,
            ),
            texto(
                "director_ejecutivo",
                4,
                "Ya salió una transferencia de USD 31.200 a una cuenta del atacante. "
                "¿Qué decide y a quién involucra?",
                [
                    "Contactar al banco de inmediato para intentar revertir la transferencia",
                    "Denunciar el fraude ante la Fiscalía",
                    "Informar a la junta directiva",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=6,
            ),
            texto(
                "legal",
                4,
                "¿Qué acciones legales y regulatorias corresponden tras el fraude?",
                [
                    "Presentar la denuncia penal con la evidencia",
                    "Evaluar si hubo acceso a datos personales para notificar a la autoridad",
                    "Mantener la cadena de custodia de la evidencia",
                ],
                dificultad=Nivel.ALTO,
                puntaje=15,
                minutos=6,
            ),
            seleccion(
                "ciso",
                4,
                "¿Qué control de proceso evitaría que se repita este fraude?",
                [
                    (
                        (
                            "Doble verificación telefónica de todo cambio de cuenta "
                            "bancaria o pago urgente"
                        ),
                        True,
                    ),
                    ("Prohibir el uso del correo electrónico en Tesorería", False),
                    ("Aumentar el límite diario de transferencias", False),
                ],
            ),
        ],
    )
