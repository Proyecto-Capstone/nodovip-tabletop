// Debrief (hot wash) de una sesión finalizada y resumen del participante (PC-45).

import { api } from './client'

export type EstadoDebrief = 'sin_iniciar' | 'borrador' | 'completado'
export type PrioridadAccion = 'alta' | 'media' | 'baja'

export interface AccionMejora {
  descripcion: string
  prioridad: PrioridadAccion
  /** Rol responsable; null = toda la organización. */
  rol_codigo: string | null
  /** Fecha ISO (AAAA-MM-DD). */
  plazo: string | null
}

export interface AccionConResponsable extends AccionMejora {
  responsable: string
}

export interface Debrief {
  sesion_id: string
  sesion_nombre: string
  cliente: string | null
  finalizada_en: string | null
  estado: EstadoDebrief
  fortalezas: string[]
  mejoras: string[]
  acciones: AccionConResponsable[]
  actualizado_en: string | null
  completado_en: string | null
  puede_editar: boolean
  roles: { codigo: string; nombre: string }[]
}

export interface DebriefEntrada {
  fortalezas: string[]
  mejoras: string[]
  acciones: AccionMejora[]
}

export interface Lecciones {
  fortalezas: string[]
  mejoras: string[]
  acciones: AccionConResponsable[]
}

export interface TareaResumen {
  inject_orden: number
  inject_titulo: string
  enunciado: string
  tipo: 'texto_libre' | 'seleccion_multiple'
  puntaje_maximo: number
  respondida: boolean
  respuesta: string | null
  puntaje: number
  aciertos: string[]
  faltantes: string[]
  errores: string[]
  opciones_correctas: string[]
  ajuste_motivo: string | null
}

export interface ResumenParticipante {
  sesion_id: string
  nombre: string
  finalizada_en: string | null
  rol_nombre: string
  puntaje: number
  maximo: number
  porcentaje: number
  posicion: number
  total_participantes: number
  tareas: TareaResumen[]
  lecciones: Lecciones | null
}

export const rutasDebrief = {
  debrief: (id: string) => `/sesiones/${id}/debrief`,
  resumen: (id: string) => `/mis-sesiones/${id}/resumen`,
}

export const guardarDebrief = (id: string, datos: DebriefEntrada) =>
  api<Debrief>(rutasDebrief.debrief(id), { metodo: 'PUT', cuerpo: datos })

export const completarDebrief = (id: string) =>
  api<Debrief>(`${rutasDebrief.debrief(id)}/completar`, { metodo: 'POST' })

export const reabrirDebrief = (id: string) =>
  api<Debrief>(`${rutasDebrief.debrief(id)}/reabrir`, { metodo: 'POST' })

export const ETIQUETA_PRIORIDAD: Record<PrioridadAccion, string> = {
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
}

/** "2026-12-15" → "15 dic 2026", sin desfase por zona horaria. */
export function formatoPlazo(plazo: string | null) {
  if (!plazo) return '—'
  const [a, m, d] = plazo.split('-').map(Number)
  return new Date(a, m - 1, d).toLocaleDateString('es-EC', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}
