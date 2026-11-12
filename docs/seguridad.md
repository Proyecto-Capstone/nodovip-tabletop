# Seguridad, calidad y accesibilidad (PC-47)

Este documento resume los controles de seguridad de la plataforma frente al
**OWASP Top 10 (2021)**, la cobertura de pruebas y la auditoría de
accesibilidad **WCAG 2.1 AA**. Corresponde a los requisitos RNF-01 (control de
acceso), RNF-02 (protección de datos), RNF-06 (usabilidad), RNF-07 (responsive)
y RNF-08 (mantenibilidad).

## 1. Cabeceras de seguridad HTTP (NGINX)

Se configuran en `nginx/default.conf.template` con `always`, para que también
acompañen a las respuestas de error.

| Cabecera | Valor | Protege contra |
|---|---|---|
| `Content-Security-Policy` | Estricta en Staging/Demo: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'` | XSS e inyección de recursos externos |
| `X-Frame-Options` | `DENY` | Clickjacking (además de `frame-ancestors 'none'`) |
| `X-Content-Type-Options` | `nosniff` | Ejecución de archivos con un tipo MIME falso |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Filtración de URL internas a sitios externos |
| `Permissions-Policy` | Cámara, micrófono, geolocalización, pagos y USB deshabilitados | Abuso de APIs del navegador |
| `Cross-Origin-Opener-Policy` | `same-origin` | Ataques entre ventanas (tabnabbing, XS-Leaks) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (solo Staging/Demo, con HTTPS) | Degradación a HTTP |

Otros ajustes:

- `server_tokens off`: no se publica la versión de NGINX.
- `client_max_body_size 1m`: la API solo recibe JSON pequeño.

La política de contenido cambia según el ambiente mediante la variable
`NGINX_CSP`:

- `docker-compose.yml` usa la política estricta.
- `docker-compose.override.yml` (local) permite el script en línea de React
  Refresh y el WebSocket de recarga de Vite (`ws:`).

`style-src 'unsafe-inline'` es necesario porque React aplica estilos en línea
(los anchos de las barras de avance). No habilita la ejecución de scripts.

**Verificación:** el frontend compilado se probó con la política estricta en
Google Chrome. La aplicación, el reporte, el leaderboard y el WebSocket
funcionaron sin bloqueos en la consola.

## 2. Revisión OWASP Top 10 (2021)

| Riesgo | Control en la plataforma |
|---|---|
| **A01 Control de acceso roto** | Permisos por rol (`requiere_permiso`, matriz en `domain/usuarios.py`). El moderador solo accede a sus sesiones y el participante solo a las sesiones a las que fue invitado: lo ajeno o lo que no existe responde **404**, para no revelar que existe. Hay pruebas de API de cada permiso por rol. |
| **A02 Fallas criptográficas** | Contraseñas con bcrypt de 12 rondas. JWT HS256 con un secreto de 32 caracteres o más, obligatorio fuera de local. HSTS en los ambientes con HTTPS. |
| **A03 Inyección** | Solo se usan consultas parametrizadas de SQLAlchemy (sin SQL armado a mano). El texto de los participantes se escapa en el PDF (`html.escape`, con prueba). React escapa por defecto (no se usa `dangerouslySetInnerHTML`). |
| **A04 Diseño inseguro** | Las respuestas son inmutables (trigger en PostgreSQL) y los ajustes de puntaje quedan auditados. Después del cierre no se aceptan respuestas ni invitaciones (con prueba). |
| **A05 Configuración insegura** | Cabeceras de la sección 1. `/docs`, `/redoc` y `/openapi.json` solo se publican en desarrollo (`urls_documentacion`, con prueba). Los errores 5xx no exponen detalles internos: el error del PDF devuelve un mensaje genérico y el detalle va al log. |
| **A06 Componentes vulnerables** | Versiones fijadas en `requirements.txt` y `package-lock.json`, y `npm audit` en la revisión. axe-core está fijado en una versión exacta. |
| **A07 Fallas de autenticación** | Bloqueo tras 5 intentos fallidos en 15 minutos (429). La cookie de sesión es `httpOnly`, `SameSite=Strict` y `Secure` fuera de local, y dura 8 h. El usuario se recarga en cada petición: desactivar a alguien corta su sesión. |
| **A08 Integridad de datos** | El CSRF se mitiga con `SameSite=Strict`. El WebSocket valida la cabecera `Origin` contra el `Host` (`origen_permitido`), lo que protege contra el secuestro de WebSocket entre sitios. |
| **A09 Registro y monitoreo** | Historial de accesos (exitosos y fallidos) en `/api/accesos`, registro de los ajustes de puntaje, monitoreo de sesiones activas y errores del servidor en el log del backend. |
| **A10 SSRF** | El backend no hace peticiones a URL que entregue el usuario. La única salida es la API de Brevo, con una URL fija. |

## 3. Cobertura de pruebas

- **Backend:** `pytest-cov` en el CI con un mínimo de **85 %**
  (`--cov-fail-under=85`). Con solo las pruebas unitarias, que son las que
  corre el CI, la cobertura es del **88 %**. Con PostgreSQL y Redis reales
  (`TEST_DATABASE_URL`, `TEST_REDIS_URL`) llega al **94 %**. Llevar esas
  pruebas de integración al CI le corresponde a PB-15 (CI/CD completo).
- **Frontend:** 111 pruebas Vitest, incluidas las nuevas de accesibilidad.

```bash
cd backend && pytest -q --cov=app --cov-report=term-missing:skip-covered
```

## 4. Accesibilidad WCAG 2.1 AA

### Auditoría

Se usó **axe-core 4.14** (Deque), con las reglas WCAG 2.0/2.1 de nivel A y
AA, sobre las pantallas reales en Google Chrome con sus estilos. Así también
se mide el contraste de colores.

| Hallazgo | Corrección |
|---|---|
| Texto secundario `#6b7085` sobre el fondo gris: 4.29:1 | `--texto-suave` pasa a `#61667a` (mínimo 4.88:1 en todos los fondos claros) |
| Insignias verdes (Activo, Exitoso…): 3.95:1 | `--verde` pasa a `#1b7343` (5.03:1) |
| Insignias rojas: 4.27:1 | `--rojo` pasa a `#b23434` (5.15:1) |
| Texto naranja y azul de acento | `--naranja` pasa a `#9a5207` (5.03:1) y `--acento` a `#2a63d8` (4.65:1) |
| Píldora de severidad "Alta" de las alertas: 3.11:1 | Fondo `#a9531a` (5.33:1) |
| Rol en el podio dorado del leaderboard: 4.02:1 | Opacidad del texto del 70 % al 85 % |
| `<html lang="en">` y título "frontend" | `lang="es"` y título "NODOVIP Tabletop" (WCAG 3.1.1 y 2.4.2) |
| Sin forma de saltar el menú con el teclado | Enlace "Saltar al contenido", visible al recibir el foco (WCAG 2.4.1) |

**Resultado:** 0 violaciones en **28 pantallas de los tres roles**:

- **Administrador y analista (13):** biblioteca, detalle, formulario nuevo y
  de edición, banco de preguntas, usuarios, accesos, reportes, reporte,
  debrief, leaderboard (lista y sesión) y monitoreo.
- **Moderador (10):** Mis tabletops, nueva sesión, los 5 pasos del diseñador,
  el panel en vivo (sesión programada y finalizada) y las respuestas.
- **Participante (5):** Mis sesiones, el detalle de una sesión programada y de
  una finalizada, la sala de espera y el resumen personal.

La pantalla de inicio de sesión se revisa con la prueba automática (sección
siguiente). Usa las mismas variables de color, que ya cumplen el contraste.

Como los colores salen de las variables del sistema de diseño (PC-43), la
corrección se aplica a todas las pantallas a la vez.

### Tema oscuro (PC-15)

La interfaz pasó a un tema oscuro que sigue al inicio de sesión. Cada color de
estado tiene ahora dos tonos: uno de **relleno** (`--verde`, `--rojo`,
`--naranja`, `--acento`, para barras y fondos con texto blanco) y otro de
**texto** (`--verde-texto`, `--rojo-texto`, `--naranja-texto`,
`--acento-texto`), que cumple al menos 4.5:1 sobre todas las superficies
oscuras. El texto secundario `--texto-suave` (`#a4a8c4`) da como mínimo
5.78:1. Se repitió la auditoría con axe-core en Chrome sobre las pantallas
rediseñadas (inicio de sesión, biblioteca, banco de preguntas, nuevo
escenario, leaderboard y reportes) con 0 violaciones.

### Pruebas automáticas

`src/test/accesibilidad.test.tsx` ejecuta axe-core en el CI sobre:

- inicio de sesión;
- usuarios;
- biblioteca;
- mis sesiones;
- resumen del participante;
- las 6 evidencias simuladas, su editor y las lecciones.

En jsdom no hay estilos reales, así que se vigilan las etiquetas, los roles,
los nombres accesibles, ARIA y la estructura. Una prueba de control comprueba
que la auditoría sí detecta un campo sin etiqueta.

### Otros criterios ya cubiertos

- Foco visible con el teclado (`:focus-visible`, desde PC-43).
- Regiones `aria-live` para los avisos en vivo (inject nuevo, reconexión).
- `prefers-reduced-motion` en las animaciones.
- Barras de avance con `role="progressbar"` y sus valores.
- Diseño responsive desde 360 px (RNF-07).

### Pendiente

Probar con lectores de pantalla reales (NVDA, VoiceOver) y con usuarios de
NODOVIP para medir RNF-06 (que el 80 % complete su primera tarea sin ayuda).
