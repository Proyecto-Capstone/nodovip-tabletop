// Tipos y llamadas del diseñador de tabletop (PB-05) e invitaciones (PB-06).

import { api } from './client'
import type { Inject, Nivel } from './escenarios'

export type EstadoSesion = 'borrador' | 'programada' | 'en_curso' | 'finalizada'
export type TipoTarea = 'texto_libre' | 'seleccion_multiple'
export type EstadoInvitacion = 'pendiente' | 'enviada' | 'fallida' | 'aceptada'

export interface Opcion {
  texto: string
  correcta: boolean
}

export interface TareaSesion {
  id: string
  inject_id: string | null
  rol_codigo: string
  tipo: TipoTarea
  enunciado: string
  opciones: Opcion[]
  criterios: string[]
  dificultad: Nivel
  puntaje_maximo: number
  tiempo_limite_segundos: number
  respuesta_esperada: string | null
}

export interface Participante {
  usuario_id: string
  rol_codigo: string
}

/** Participante tal como lo devuelve el backend, con su invitación. */
export interface ParticipanteInvitado extends Participante {
  invitacion: EstadoInvitacion
  invitacion_enviada_en: string | null
  invitacion_aceptada_en: string | null
  invitacion_error: string | null
}

export interface Pesos {
  completitud: number
  precision: number
  tiempo: number
}

export interface SesionResumen {
  id: string
  nombre: string
  /** Organización para la que se hace el ejercicio (PB-14). */
  cliente: string | null
  escenario_id: string
  estado: EstadoSesion
  fecha_programada: string | null
  duracion_minutos: number | null
  roles: string[]
  total_participantes: number
  puntaje_maximo_total: number
}

export interface SesionDetalle extends SesionResumen {
  injects: Inject[]
  tareas: TareaSesion[]
  participantes: ParticipanteInvitado[]
  pesos: Pesos
  pendientes_para_programar: string[]
}

/** Lo que guarda el asistente (PUT). Los injects llevan su id, también los nuevos. */
export interface SesionDiseno {
  nombre: string
  cliente: string | null
  roles: string[]
  injects: Omit<Inject, 'orden'>[]
  tareas: TareaSesion[]
  participantes: Participante[]
  pesos: Pesos
  fecha_programada: string | null
  duracion_minutos: number | null
}

export interface ParticipanteDisponible {
  id: string
  nombre: string
  correo: string
}

export const rutasSesiones = {
  lista: '/sesiones',
  sesion: (id: string) => `/sesiones/${id}`,
  participantes: '/sesiones/participantes-disponibles',
}

export const crearSesion = (escenario_id: string) =>
  api<SesionDetalle>('/sesiones', { metodo: 'POST', cuerpo: { escenario_id } })

export const guardarSesion = (id: string, datos: SesionDiseno) =>
  api<SesionDetalle>(`/sesiones/${id}`, { metodo: 'PUT', cuerpo: datos })

export const programarSesion = (id: string) =>
  api<SesionDetalle>(`/sesiones/${id}/programar`, { metodo: 'POST' })

export const enviarInvitaciones = (id: string) =>
  api<SesionDetalle>(`/sesiones/${id}/invitaciones`, { metodo: 'POST' })

export const eliminarSesion = (id: string) =>
  api<null>(`/sesiones/${id}`, { metodo: 'DELETE' })

export function aDiseno(s: SesionDetalle): SesionDiseno {
  return {
    nombre: s.nombre,
    cliente: s.cliente,
    roles: s.roles,
    injects: s.injects.map((i) => ({
      id: i.id,
      titulo: i.titulo,
      descripcion: i.descripcion,
      minuto_sugerido: i.minuto_sugerido,
    })),
    tareas: s.tareas,
    participantes: s.participantes.map((p) => ({
      usuario_id: p.usuario_id,
      rol_codigo: p.rol_codigo,
    })),
    pesos: s.pesos,
    fecha_programada: s.fecha_programada,
    duracion_minutos: s.duracion_minutos,
  }
}
