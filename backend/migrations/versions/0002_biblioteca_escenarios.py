"""PC-14 PC-15 biblioteca de escenarios y banco de preguntas

Crea los catálogos tipo_escenario (Tabla 6) y rol_ejercicio, y las tablas
escenario, escenario_rol, inject y tarea.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Roles organizacionales del ejercicio (Tablas 5 y 6 del documento Capstone).
ROLES_EJERCICIO = [
    ("ciso", "CISO"),
    ("director_ejecutivo", "Director Ejecutivo"),
    ("direccion", "Dirección"),
    ("legal", "Legal"),
    ("ti", "Responsable de TI"),
    ("comunicaciones", "Comunicaciones"),
    ("relaciones_publicas", "Relaciones Públicas"),
    ("operaciones", "Operaciones"),
    ("atencion_cliente", "Atención al Cliente"),
    ("rrhh", "Recursos Humanos"),
]

# Catálogo inicial de tipos de escenario (Tabla 6 del documento Capstone).
TIPOS_ESCENARIO = [
    (
        "ransomware",
        "Ransomware",
        (
            "Cifrado masivo de archivos críticos de la organización con demanda de "
            "rescate; interrupción de operaciones."
        ),
        "alto",
        ["ciso", "director_ejecutivo", "legal", "ti", "comunicaciones"],
    ),
    (
        "data_breach",
        "Data breach",
        (
            "Exfiltración de datos personales de clientes o empleados; notificación "
            "regulatoria requerida."
        ),
        "alto",
        ["legal", "ciso", "ti", "relaciones_publicas"],
    ),
    (
        "ddos",
        "Ataque DDoS",
        (
            "Saturación de servicios en línea; interrupción de la disponibilidad de "
            "plataformas críticas del negocio."
        ),
        "medio",
        ["ti", "operaciones", "atencion_cliente"],
    ),
    (
        "phishing_dirigido",
        "Phishing dirigido",
        (
            "Compromiso de credenciales de un ejecutivo mediante ingeniería social; "
            "acceso no autorizado a sistemas internos."
        ),
        "medio",
        ["rrhh", "ti", "director_ejecutivo", "legal"],
    ),
    (
        "insider_threat",
        "Insider threat",
        (
            "Empleado interno con acceso privilegiado realiza extracción no autorizada "
            "de información confidencial."
        ),
        "medio",
        ["rrhh", "legal", "ciso", "direccion"],
    ),
    (
        "fallo_proveedor",
        "Fallo de proveedor crítico",
        (
            "Caída de un proveedor de nube o servicio SaaS que compromete la "
            "continuidad operativa."
        ),
        "bajo",
        ["ti", "operaciones", "legal", "direccion"],
    ),
    (
        "cadena_suministro",
        "Compromiso de cadena de suministro",
        (
            "Ataque a través de un proveedor de software de terceros que introduce "
            "código malicioso en los sistemas de la organización."
        ),
        "alto",
        ["ti", "ciso", "legal", "direccion"],
    ),
]


def upgrade() -> None:
    rol_ejercicio = op.create_table(
        "rol_ejercicio",
        sa.Column("codigo", sa.String(40), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False),
    )
    tipo_escenario = op.create_table(
        "tipo_escenario",
        sa.Column("codigo", sa.String(40), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("nivel_complejidad", sa.String(10), nullable=False),
        sa.Column("roles_sugeridos", sa.JSON, nullable=False),
    )
    op.create_table(
        "escenario",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column(
            "tipo_codigo",
            sa.String(40),
            sa.ForeignKey("tipo_escenario.codigo"),
            nullable=False,
        ),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("nivel", sa.String(10), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("es_base", sa.Boolean, nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_escenario_tipo_codigo", "escenario", ["tipo_codigo"])
    op.create_index("ix_escenario_estado", "escenario", ["estado"])
    op.create_table(
        "escenario_rol",
        sa.Column(
            "escenario_id",
            sa.Uuid,
            sa.ForeignKey("escenario.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "rol_codigo",
            sa.String(40),
            sa.ForeignKey("rol_ejercicio.codigo"),
            primary_key=True,
        ),
    )
    op.create_table(
        "inject",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "escenario_id",
            sa.Uuid,
            sa.ForeignKey("escenario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("orden", sa.SmallInteger, nullable=False),
        sa.Column("titulo", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("minuto_sugerido", sa.SmallInteger, nullable=True),
        sa.UniqueConstraint("escenario_id", "orden"),
    )
    op.create_index("ix_inject_escenario_id", "inject", ["escenario_id"])
    op.create_table(
        "tarea",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "escenario_id",
            sa.Uuid,
            sa.ForeignKey("escenario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("posicion", sa.SmallInteger, nullable=False),
        sa.Column(
            "rol_codigo",
            sa.String(40),
            sa.ForeignKey("rol_ejercicio.codigo"),
            nullable=False,
        ),
        sa.Column("enunciado", sa.Text, nullable=False),
        sa.Column("dificultad", sa.String(10), nullable=False),
        sa.Column("criterios", sa.JSON, nullable=False),
        sa.Column("puntaje_maximo", sa.SmallInteger, nullable=False),
        sa.Column("tiempo_limite_segundos", sa.Integer, nullable=False),
        sa.Column("respuesta_esperada", sa.Text, nullable=True),
    )
    op.create_index("ix_tarea_escenario_id", "tarea", ["escenario_id"])
    op.create_index("ix_tarea_rol_codigo", "tarea", ["rol_codigo"])
    op.create_index("ix_tarea_dificultad", "tarea", ["dificultad"])

    op.bulk_insert(
        rol_ejercicio, [{"codigo": c, "nombre": n} for c, n in ROLES_EJERCICIO]
    )
    op.bulk_insert(
        tipo_escenario,
        [
            {
                "codigo": c,
                "nombre": n,
                "descripcion": d,
                "nivel_complejidad": nivel,
                "roles_sugeridos": roles,
            }
            for c, n, d, nivel, roles in TIPOS_ESCENARIO
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_tarea_dificultad", table_name="tarea")
    op.drop_index("ix_tarea_rol_codigo", table_name="tarea")
    op.drop_index("ix_tarea_escenario_id", table_name="tarea")
    op.drop_table("tarea")
    op.drop_index("ix_inject_escenario_id", table_name="inject")
    op.drop_table("inject")
    op.drop_table("escenario_rol")
    op.drop_index("ix_escenario_estado", table_name="escenario")
    op.drop_index("ix_escenario_tipo_codigo", table_name="escenario")
    op.drop_table("escenario")
    op.drop_table("tipo_escenario")
    op.drop_table("rol_ejercicio")
