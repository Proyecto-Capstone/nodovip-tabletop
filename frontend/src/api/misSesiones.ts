// Sesiones del participante y aceptación de la invitación (PB-06).

import { api } from './client'
import type { EstadoInvitacion, EstadoSesion } from './sesiones'

export interface MiSesion {
  id: string
  nombre: string
  estado: EstadoSesion
  fecha_programada: string | null
  duracion_minutos: number | null
  escenario_nombre: string
  escenario_descripcion: string
  moderador_nombre: string
  rol_codigo: string
  rol_nombre: string
  total_participantes: number
  invitacion: EstadoInvitacion
  invitacion_aceptada_en: string | null
}

export const rutasMisSesiones = {
  lista: '/mis-sesiones',
  sesion: (id: string) => `/mis-sesiones/${id}`,
}

export const aceptarInvitacion = (id: string) =>
  api<MiSesion>(`/mis-sesiones/${id}/aceptar`, { metodo: 'POST' })
