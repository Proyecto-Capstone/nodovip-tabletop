// Motor en tiempo real (PB-07): comandos del moderador y vista en vivo.

import { api } from './client'
import type { EstadoSesion } from './sesiones'

export interface VistaEnVivo {
  sesion_id: string
  nombre: string
  estado: EstadoSesion
  total_injects: number
  inject_actual: number
  inject: { orden: number; titulo: string; descripcion: string } | null
  pausada: boolean
  iniciada_en: string | null
  inject_lanzado_en: string | null
  segundos_transcurridos: number
  duracion_minutos: number | null
  version: number
  total_conectados: number
  /** Solo para el moderador. */
  conectados: string[] | null
}

export type ComandoEnVivo = 'iniciar' | 'lanzar-inject' | 'pausar' | 'reanudar' | 'cerrar'

export const comandoEnVivo = (sesionId: string, comando: ComandoEnVivo) =>
  api<VistaEnVivo>(`/sesiones/${sesionId}/en-vivo/${comando}`, { metodo: 'POST' })

export function urlWebSocket(sesionId: string) {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocolo}://${window.location.host}/api/ws/sesiones/${sesionId}`
}

/** Cierres del servidor que no se arreglan reconectando. */
export const CIERRE_DEFINITIVO: Record<number, string> = {
  4401: 'Tu sesión expiró. Vuelve a iniciar sesión.',
  4403: 'Tu rol no puede seguir esta sesión.',
  4404: 'No encontramos esta sesión entre las tuyas.',
}
