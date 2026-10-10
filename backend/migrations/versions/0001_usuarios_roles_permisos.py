"""PC-11 usuarios, roles y permisos

Crea las tablas rol, permiso, rol_permiso y usuario, y carga los 5 roles del
sistema con sus permisos (mínimo privilegio).

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Datos fijos de esta migración. No importar desde app/: una migración no debe
# cambiar si el código cambia después.
ROLES = [
    ("administrador", "Gestiona usuarios, escenarios base y monitorea sesiones"),
    ("moderador", "Diseña y conduce sesiones tabletop"),
    ("participante", "Responde tareas e injects según su rol en la sesión"),
    ("observador", "Ve el leaderboard en modo lectura"),
    ("analista", "Genera y consulta reportes de brechas"),
]

PERMISOS = [
    ("usuarios:gestionar", "Crear, editar, desactivar y asignar roles"),
    ("escenarios:gestionar", "Crear, editar y publicar escenarios base"),
    ("escenarios:leer", "Consultar la biblioteca de escenarios"),
    ("sesiones:disenar", "Diseñar y programar sesiones tabletop"),
    ("sesiones:conducir", "Iniciar, pausar, lanzar injects y cerrar sesiones"),
    ("sesiones:participar", "Unirse a una sesión y enviar respuestas"),
    ("sesiones:monitorear", "Ver todas las sesiones activas"),
    ("leaderboard:ver", "Ver el tablero de puntuación"),
    ("reportes:generar", "Generar reportes PDF de brechas"),
    ("reportes:ver", "Consultar reportes generados"),
]

ROL_PERMISOS = {
    "administrador": [
        "usuarios:gestionar",
        "escenarios:gestionar",
        "escenarios:leer",
        "sesiones:monitorear",
        "leaderboard:ver",
        "reportes:ver",
    ],
    "moderador": [
        "escenarios:leer",
        "sesiones:disenar",
        "sesiones:conducir",
        "leaderboard:ver",
        "reportes:ver",
    ],
    "participante": ["sesiones:participar"],
    "observador": ["leaderboard:ver"],
    "analista": ["reportes:generar", "reportes:ver"],
}


def upgrade() -> None:
    rol = op.create_table(
        "rol",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(30), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=False),
    )
    permiso = op.create_table(
        "permiso",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=False),
    )
    op.create_table(
        "rol_permiso",
        sa.Column(
            "rol_id",
            sa.SmallInteger,
            sa.ForeignKey("rol.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permiso_id",
            sa.SmallInteger,
            sa.ForeignKey("permiso.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("correo", sa.String(255), nullable=False, unique=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("rol_id", sa.SmallInteger, sa.ForeignKey("rol.id"), nullable=False),
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
    op.create_index("ix_usuario_rol_id", "usuario", ["rol_id"])

    op.bulk_insert(rol, [{"nombre": n, "descripcion": d} for n, d in ROLES])
    op.bulk_insert(permiso, [{"codigo": c, "descripcion": d} for c, d in PERMISOS])

    conn = op.get_bind()
    for rol_nombre, codigos in ROL_PERMISOS.items():
        for codigo in codigos:
            conn.execute(
                sa.text(
                    "INSERT INTO rol_permiso (rol_id, permiso_id) "
                    "SELECT r.id, p.id FROM rol r, permiso p "
                    "WHERE r.nombre = :rol AND p.codigo = :codigo"
                ),
                {"rol": rol_nombre, "codigo": codigo},
            )


def downgrade() -> None:
    op.drop_index("ix_usuario_rol_id", table_name="usuario")
    op.drop_table("usuario")
    op.drop_table("rol_permiso")
    op.drop_table("permiso")
    op.drop_table("rol")
