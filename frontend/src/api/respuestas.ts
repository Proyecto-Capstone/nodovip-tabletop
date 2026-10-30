// Registro trazable de respuestas (PB-09) y su puntaje (PB-10).
// Las respuestas son de solo lectura; el puntaje se ajusta agregando un registro.

import { api } from './client'
import type { TipoTarea } from './sesiones'

export interface AjustePuntaje {
  id: string
  puntaje_anterior: number
  puntaje_nuevo: number
  motivo: string
  creado_en: string
}

export interface RespuestaRegistrada {
  id: string
  /** Hora del servidor al recibirla. */
  recibida_en: string
  /** Segundos efectivos que usó el participante (sin contar pausas). */
  segundos_usados: number
  participante_id: string
  participante_nombre: string
  participante_correo: string
  rol_codigo: string
  rol_nombre: string
  inject_orden: number
  inject_titulo: string
  tarea_id: string
  tarea_enunciado: string
  tipo: TipoTarea
  tiempo_limite_segundos: number
  texto: string | null
  opciones_elegidas: number[]
  opciones_elegidas_texto: string[]
  /** Vigente: el del último ajuste o, si no hay, el automático. */
  puntaje: number
  puntaje_automatico: number
  puntaje_maximo: number
  /** Aspectos de la evaluación automática, de 0 a 1. */
  completitud: number
  precision: number
  tiempo: number
  aciertos: string[]
  faltantes: string[]
  errores: string[]
  /** Del más antiguo al más reciente. */
  ajustes: AjustePuntaje[]
}

export interface Acumulado {
  puntaje: number
  maximo: number
  porcentaje: number
  respondidas: number
  sin_responder: number
}

export interface PuntajeParticipante extends Acumulado {
  usuario_id: string
  nombre: string
  rol_codigo: string
  rol_nombre: string
}

export interface PuntajeRol extends Acumulado {
  rol_codigo: string
  rol_nombre: string
  participantes: number
}

export interface PuntajesSesion {
  participantes: PuntajeParticipante[]
  roles: PuntajeRol[]
}

export const rutaRespuestas = (sesionId: string) => `/sesiones/${sesionId}/respuestas`
export const rutaPuntajes = (sesionId: string) => `/sesiones/${sesionId}/puntajes`

export const ajustarPuntaje = (
  sesionId: string,
  respuestaId: string,
  datos: { puntaje: number; motivo: string },
) =>
  api<RespuestaRegistrada>(`/sesiones/${sesionId}/respuestas/${respuestaId}/ajustes`, {
    metodo: 'POST',
    cuerpo: datos,
  })
