// Leaderboard en vivo para observadores (PB-12). El Observador y el
// Administrador ven cualquier sesión en curso o finalizada; el Moderador,
// solo las suyas. Nunca incluye texto de respuestas, opciones ni criterios.

import { api } from './client'
import type { EstadoSesion } from './sesiones'

export interface SesionLeaderboard {
  id: string
  nombre: string
  estado: EstadoSesion
  total_injects: number
  inject_actual: number
  iniciada_en: string | null
  finalizada_en: string | null
}

export interface PosicionParticipante {
  posicion: number
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

export interface PosicionRol {
  posicion: number
  rol_codigo: string
  rol_nombre: string
  participantes: number
  puntaje: number
  maximo: number
  porcentaje: number
  respondidas: number
  sin_responder: number
}

export interface Leaderboard {
  sesion: SesionLeaderboard
  actualizado_en: string
  participantes: PosicionParticipante[]
  roles: PosicionRol[]
}

export const rutaSesionesLeaderboard = '/leaderboard/sesiones'
export const rutaLeaderboard = (sesionId: string) => `/leaderboard/sesiones/${sesionId}`

export const sesionesDelLeaderboard = () =>
  api<SesionLeaderboard[]>(rutaSesionesLeaderboard)

export const leaderboardDeLaSesion = (sesionId: string) =>
  api<Leaderboard>(rutaLeaderboard(sesionId))

export function urlWebSocketLeaderboard(sesionId: string) {
  const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocolo}://${window.location.host}/api/ws/leaderboard/${sesionId}`
}

/** Cierres del servidor que no se arreglan reconectando. */
export const CIERRE_DEFINITIVO: Record<number, string> = {
  4401: 'Tu sesión expiró. Vuelve a iniciar sesión.',
  4403: 'No tienes permiso para ver el leaderboard.',
  4404: 'No encontramos esta sesión entre las visibles.',
}
