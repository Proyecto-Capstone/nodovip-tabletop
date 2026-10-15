// Cliente HTTP de la API. Todas las rutas van bajo /api (NGINX las envía al backend).
// La sesión viaja sola en una cookie httpOnly: el código no la ve ni la guarda.

const BASE = '/api'

export type RolSistema =
  | 'administrador'
  | 'moderador'
  | 'participante'
  | 'observador'
  | 'analista'

// Aviso cuando el backend responde 401: la sesión venció, se cerró en otra
// pestaña o la cuenta fue desactivada. SesionProvider se suscribe.
let alPerderSesion: (() => void) | null = null

export function avisarAlPerderSesion(funcion: () => void) {
  alPerderSesion = funcion
  return () => {
    if (alPerderSesion === funcion) alPerderSesion = null
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
    credentials: 'same-origin',
    headers:
      opciones.cuerpo !== undefined
        ? { 'Content-Type': 'application/json' }
        : undefined,
    body:
      opciones.cuerpo !== undefined ? JSON.stringify(opciones.cuerpo) : undefined,
  })
  const texto = await respuesta.text()
  const cuerpo = texto ? JSON.parse(texto) : null
  if (!respuesta.ok) {
    // Un login fallido también es 401, pero ahí no había sesión que perder.
    if (respuesta.status === 401 && ruta !== '/auth/login') alPerderSesion?.()
    throw new ApiError(respuesta.status, extraerErrores(respuesta.status, cuerpo))
  }
  return cuerpo as T
}
