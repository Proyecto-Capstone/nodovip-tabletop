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

// --- Tareas del rol y respuestas (PB-08) ---------------------------------------------

export type EstadoTarea = 'pendiente' | 'respondida' | 'vencida'

export interface TareaParticipante {
  id: string
  inject_orden: number
  tipo: 'texto_libre' | 'seleccion_multiple'
  enunciado: string
  /** Solo el texto de cada opción: la correcta no se envía al participante. */
  opciones: string[]
  tiempo_limite_segundos: number
  segundos_restantes: number
  estado: EstadoTarea
  respuesta: { texto: string | null; opciones_elegidas: number[]; recibida_en: string } | null
}

export const rutaTareas = (sesionId: string) => `/mis-sesiones/${sesionId}/tareas`

export const responderTarea = (
  sesionId: string,
  tareaId: string,
  datos: { texto?: string; opciones?: number[] },
) =>
  api<TareaParticipante>(`/mis-sesiones/${sesionId}/tareas/${tareaId}/respuesta`, {
    metodo: 'POST',
    cuerpo: datos,
  })
