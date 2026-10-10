# Modelo de datos — Usuarios, roles y permisos (PC-11)

Base de PB-01 (autenticación y acceso por rol), PB-02 (gestión de usuarios) y del C4 Nivel 4 de la sección 7.1.

## Diagrama Entidad–Relación

```mermaid
erDiagram
    ROL ||--o{ USUARIO : "asignado a"
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

## Pendiente para otras historias

- **Historial de accesos** (usuario, fecha/hora, IP, resultado): se agrega en PB-01.
