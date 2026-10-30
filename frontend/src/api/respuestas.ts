// Registro trazable de respuestas de una sesión (PB-09). Solo lectura.

import type { TipoTarea } from './sesiones'

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
}

export const rutaRespuestas = (sesionId: string) => `/sesiones/${sesionId}/respuestas`
