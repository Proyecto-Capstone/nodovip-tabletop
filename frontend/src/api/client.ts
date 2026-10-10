// Cliente HTTP de la API. Todas las rutas van bajo /api (NGINX las envía al backend).

const BASE = '/api'
const CLAVE_ROL = 'nodovip.rolDebug'

export type RolSistema =
  | 'administrador'
  | 'moderador'
  | 'participante'
  | 'observador'
  | 'analista'

// TEMPORAL hasta PB-01: el rol se guarda en el navegador y viaja en la cabecera
// X-Rol-Debug. El backend solo la acepta en los ambientes local y test.
export function leerRolGuardado(): RolSistema {
  try {
    const guardado = localStorage.getItem(CLAVE_ROL)
    if (guardado) return guardado as RolSistema
  } catch {
    // localStorage puede no estar disponible (modo privado)
  }
  return 'administrador'
}

export function guardarRol(rol: RolSistema) {
  try {
    localStorage.setItem(CLAVE_ROL, rol)
  } catch {
    // sin almacenamiento, el rol dura solo esta sesión
  }
}

export class ApiError extends Error {
  status: number
  errores: string[]

  constructor(status: number, errores: string[]) {
    super(errores.join('; ') || `Error ${status}`)
    this.status = status
    this.errores = errores
  }
}

type DetalleValidacion = { loc?: (string | number)[]; msg?: string }

function extraerErrores(status: number, cuerpo: unknown): string[] {
  const detail = (cuerpo as { detail?: unknown } | null)?.detail
  if (detail && typeof detail === 'object' && 'errores' in detail) {
    return (detail as { errores: string[] }).errores
  }
  if (Array.isArray(detail)) {
    return (detail as DetalleValidacion[]).map((d) => {
      const campo = (d.loc ?? []).filter((p) => p !== 'body').join(' → ')
      return campo ? `${campo}: ${d.msg}` : String(d.msg)
    })
  }
  if (typeof detail === 'string') return [detail]
  if (status === 401) return ['No autenticado']
  if (status === 403) return ['No tienes permiso para esta acción']
  return [`Error ${status}`]
}

export async function api<T>(
  ruta: string,
  opciones: { metodo?: string; cuerpo?: unknown } = {},
): Promise<T> {
  const respuesta = await fetch(BASE + ruta, {
    method: opciones.metodo ?? 'GET',
    headers: {
      'X-Rol-Debug': leerRolGuardado(),
      ...(opciones.cuerpo !== undefined
        ? { 'Content-Type': 'application/json' }
        : {}),
    },
    body:
      opciones.cuerpo !== undefined ? JSON.stringify(opciones.cuerpo) : undefined,
  })
  const texto = await respuesta.text()
  const cuerpo = texto ? JSON.parse(texto) : null
  if (!respuesta.ok) {
    throw new ApiError(respuesta.status, extraerErrores(respuesta.status, cuerpo))
  }
  return cuerpo as T
}
