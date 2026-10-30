// Reporte de brechas de una sesión finalizada (PB-14).

import { api } from './client'

export type EstadoPdf = 'generando' | 'generado' | 'fallido'
export type Severidad = 'alta' | 'media' | 'baja'

export interface EstadoReporte {
  estado: EstadoPdf
  solicitado_en: string
  generado_en: string | null
  error: string | null
}

export interface SesionConReporte {
  id: string
  nombre: string
  cliente: string | null
  finalizada_en: string | null
  participantes: number
  reporte: EstadoReporte | null
}

export interface FilaPuntaje {
  nombre: string
  /** Rol del participante o número de participantes del rol. */
  detalle: string
  puntaje: number
  maximo: number
  porcentaje: number
  respondidas: number
  sin_responder: number
}

export interface Brecha {
  participante: string
  rol_codigo: string
  rol_nombre: string
  tarea: string
  inject_orden: number
  tipo: string
  tipo_etiqueta: string
  severidad: Severidad
  porcentaje: number
  detalle: string[]
  /** En cuántas sesiones anteriores del mismo cliente apareció. */
  recurrente_en: number
}

export interface RespuestaReporte {
  recibida_en: string
  participante: string
  rol_nombre: string
  inject_orden: number
  tarea: string
  contenido: string
  puntaje: number
  puntaje_maximo: number
  ajustada: boolean
}

export interface Recomendacion {
  prioridad: Severidad
  rol_nombre: string
  texto: string
  recurrente: boolean
}

export interface Reporte {
  sesion_id: string
  nombre: string
  cliente: string | null
  escenario: string
  moderador: string
  iniciada_en: string | null
  finalizada_en: string | null
  duracion_segundos: number | null
  participantes: number
  injects_lanzados: number
  total_injects: number
  puntaje_total: number
  maximo_total: number
  porcentaje_total: number
  por_participante: FilaPuntaje[]
  por_rol: FilaPuntaje[]
  brechas: Brecha[]
  superadas: Brecha[]
  respuestas: RespuestaReporte[]
  recomendaciones: Recomendacion[]
  sesiones_anteriores: number
  pdf: EstadoReporte | null
}

export const rutasReportes = {
  lista: '/reportes',
  reporte: (id: string) => `/reportes/${id}`,
  /** Descarga directa (la cookie de sesión viaja sola: mismo origen). */
  pdf: (id: string) => `/api/reportes/${id}/pdf`,
}

export const regenerarPdf = (id: string) =>
  api<EstadoReporte>(`/reportes/${id}/regenerar`, { metodo: 'POST' })
