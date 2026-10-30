// Monitoreo de sesiones activas (PC-24, RNF). Solo Administrador (permiso
// sesiones:monitorear). Nunca incluye texto de respuestas, opciones elegidas
// ni criterios: solo el acumulado (PB-10), igual que el leaderboard.

import { api } from './client'

export interface FilaMonitoreo {
  id: string
  nombre: string
  moderador_nombre: string
  escenario_nombre: string
  pausada: boolean
  invitados: number
  conectados: number
  inject_actual: number
  total_injects: number
  respuestas_recibidas: number
  respuestas_esperadas: number
  porcentaje_avance: number
  segundos_transcurridos: number
  iniciada_en: string | null
  duracion_minutos: number | null
  // La sesión lleva más tiempo corrido que su duración programada: podría
  // estar abandonada (el moderador nunca la cerró).
  excede_duracion: boolean
}

export interface ResumenMonitoreo {
  activas: number
  maximo: number
  sesiones: FilaMonitoreo[]
}

export interface PuntajeParticipanteMonitoreo {
  usuario_id: string
  nombre: string
  rol_codigo: string
  rol_nombre: string
  puntaje: number
  maximo: number
  porcentaje: number
  respondidas: number
  sin_responder: number
}

export interface PuntajeRolMonitoreo {
  rol_codigo: string
  rol_nombre: string
  participantes: number
  puntaje: number
  maximo: number
  porcentaje: number
  respondidas: number
  sin_responder: number
}

export interface DetalleMonitoreo {
  sesion: FilaMonitoreo
  participantes: PuntajeParticipanteMonitoreo[]
  roles: PuntajeRolMonitoreo[]
  // Quién está conectado ahora, no solo el conteo de FilaMonitoreo.conectados.
  conectados_ids: string[]
}

export const rutaSesionesMonitoreo = '/monitoreo/sesiones'
export const rutaDetalleMonitoreo = (sesionId: string) => `/monitoreo/sesiones/${sesionId}`

export const sesionesActivas = () => api<ResumenMonitoreo>(rutaSesionesMonitoreo)

export const detalleDeLaSesion = (sesionId: string) =>
  api<DetalleMonitoreo>(rutaDetalleMonitoreo(sesionId))

export function urlWebSocketMonitoreo(sesionId: string) {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocolo}://${window.location.host}/api/ws/monitoreo/${sesionId}`
}

/** Cierres del servidor que no se arreglan reconectando. */
export const CIERRE_DEFINITIVO: Record<number, string> = {
  4401: 'Tu sesión expiró. Vuelve a iniciar sesión.',
  4403: 'No tienes permiso para monitorear sesiones.',
  4404: 'Esta sesión ya no está en curso.',
}
