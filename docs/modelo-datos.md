# Modelo de datos — Usuarios, roles, permisos y accesos (PC-11, PC-12)

Base de PB-01 (autenticación y acceso por rol), PB-02 (gestión de usuarios) y del C4 Nivel 4 de la sección 7.1.

## Diagrama Entidad–Relación

```mermaid
erDiagram
    ROL ||--o{ USUARIO : "asignado a"
    USUARIO |o--o{ ACCESO : "registra"
    ROL ||--o{ ROL_PERMISO : tiene
    PERMISO ||--o{ ROL_PERMISO : "otorgado en"

    USUARIO {
        uuid id PK
        varchar correo UK "único, indexado"
        varchar nombre
        varchar password_hash "bcrypt"
        boolean activo
        smallint rol_id FK
        timestamptz creado_en
        timestamptz actualizado_en
    }
    ROL {
        smallint id PK
        varchar nombre UK
        varchar descripcion
    }
    PERMISO {
        smallint id PK
        varchar codigo UK "ej. usuarios:gestionar"
        varchar descripcion
    }
    ROL_PERMISO {
        smallint rol_id PK, FK
        smallint permiso_id PK, FK
    }
    ACCESO {
        bigint id PK "identity"
        uuid usuario_id FK "NULL si el correo no existe; RESTRICT"
        varchar correo_ingresado
        timestamptz fecha_hora
        varchar ip "IPv4 o IPv6"
        varchar user_agent
        varchar resultado "CHECK: exitoso, credenciales_invalidas, usuario_inactivo, bloqueado"
    }
```

## Decisiones de diseño

- **Un rol por usuario** (relación N:1). PB-02 pide asignar y cambiar "el rol" de cada usuario.
- **Permisos por rol** (N:M en `rol_permiso`). Permite aplicar mínimo privilegio (RNF-01) sin cambiar código: se agregan filas, no `if` por rol.
- **UUID en `usuario.id`**: los identificadores no son predecibles en URLs ni en tokens.
- **`correo` único** (la restricción UNIQUE crea su índice): es el dato de login.
- **`password_hash`**: nunca se guarda la contraseña en texto plano; se usa bcrypt (RNF-02).
- **`activo`** en lugar de borrar: un usuario desactivado conserva su historial para auditoría.
- **Fechas con zona horaria** (`timestamptz`) para trazabilidad.

## Matriz de roles y permisos (carga inicial)

| Permiso | Administrador | Moderador | Participante | Observador | Analista |
|---|:-:|:-:|:-:|:-:|:-:|
| usuarios:gestionar | ✅ | | | | |
| escenarios:gestionar | ✅ | | | | |
| escenarios:leer | ✅ | ✅ | | | |
| sesiones:disenar | | ✅ | | | |
| sesiones:conducir | | ✅ | | | |
| sesiones:participar | | | ✅ | | |
| sesiones:monitorear | ✅ | | | | |
| leaderboard:ver | ✅ | ✅ | | ✅ | |
| reportes:generar | | | | | ✅ |
| reportes:ver | ✅ | ✅ | | | ✅ |

La matriz vive en dos lugares que deben coincidir: `backend/app/domain/usuarios.py` (`PERMISOS_POR_ROL`) y la migración `0001`. Si cambia, se crea una migración nueva.

## Historial de accesos (PB-01, migración 0003)

- **Una fila por intento de login**, exitoso o no (RNF-01). Ver `docs/autenticacion.md`.
- **`usuario_id` nullable:** también se registran intentos con correos que no existen.
- **FK `RESTRICT`:** una cuenta con accesos no se puede eliminar, solo desactivar.
- **Índices** `(usuario_id, fecha_hora DESC)`, `(correo_ingresado, fecha_hora DESC)`
  (para el bloqueo por intentos fallidos) y `(fecha_hora DESC)` (para el listado).
