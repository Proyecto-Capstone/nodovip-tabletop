# Gestión de usuarios y roles (PB-02)

Módulo M4, requisito RF-05. Usa el modelo de datos de `docs/modelo-datos.md`.

## Reglas de negocio

| Regla | Detalle |
|---|---|
| Solo el Administrador gestiona usuarios | Permiso `usuarios:gestionar`; otros roles reciben 403 |
| Correo único | Se guarda en minúsculas y sin espacios; un duplicado responde 409 |
| Correo con formato válido | Validado con `email-validator` |
| Todo usuario tiene un rol | Uno de los 5 roles del sistema (RF-05) |
| Contraseña cifrada | bcrypt con 12 rondas (RNF-02); el hash nunca sale en la API |
| Política de contraseñas | Mínimo 10 caracteres, mayúscula, minúscula y número; sin espacios al inicio o final; máximo 72 bytes (límite de bcrypt) |
| Desactivar antes de eliminar | Desactivar conserva el historial para auditoría. Solo una cuenta inactiva se puede eliminar definitivamente, y solo si no tiene registros asociados (409) |
| Siempre queda un Administrador activo | No se puede desactivar ni cambiar el rol del último administrador activo (422) |

## Endpoints

Todos requieren el permiso `usuarios:gestionar`.

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/usuarios?q=&rol=&activo=` | Listar con búsqueda por nombre o correo y filtros |
| GET | `/api/usuarios/{id}` | Detalle |
| POST | `/api/usuarios` | Crear (`nombre`, `correo`, `contrasena`, `rol`) |
| PUT | `/api/usuarios/{id}` | Editar nombre, correo y rol |
| POST | `/api/usuarios/{id}/desactivar` | Desactivar |
| POST | `/api/usuarios/{id}/activar` | Reactivar |
| POST | `/api/usuarios/{id}/contrasena` | Restablecer contraseña (`contrasena`) |
| DELETE | `/api/usuarios/{id}` | Eliminar definitivamente (solo cuentas inactivas) |

## Primer administrador de cada ambiente

```bash
docker compose exec backend python -m app.crear_admin
```

Pide nombre, correo y contraseña por consola. La contraseña no se muestra ni queda en el historial de la terminal.

## Pendiente para PB-01

- Login con correo y contraseña (usa `HasherContrasenas.verificar`).
- Reemplazar la cabecera temporal `X-Rol-Debug` por el token.
- Historial de accesos (usuario, fecha/hora, IP, resultado).
