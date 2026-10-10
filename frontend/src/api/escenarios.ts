// Tipos y llamadas de la biblioteca de escenarios (PB-03, PB-04).

import { api } from './client'

export type Nivel = 'bajo' | 'medio' | 'alto'
export type EstadoEscenario = 'borrador' | 'publicado' | 'archivado'

export interface TipoEscenario {
  codigo: string
  nombre: string
  descripcion: string
  nivel_complejidad: Nivel
  roles_sugeridos: string[]
}

export interface RolEjercicio {
  codigo: string
  nombre: string
}

export interface Inject {
  id: string
  orden: number
  titulo: string
  descripcion: string
  minuto_sugerido: number | null
}

export interface Tarea {
  id: string
  enunciado: string
  rol_codigo: string
  dificultad: Nivel
  criterios: string[]
  puntaje_maximo: number
  tiempo_limite_segundos: number
  respuesta_esperada: string | null
}

export interface EscenarioResumen {
  id: string
  nombre: string
  tipo_codigo: string
  nivel: Nivel
  estado: EstadoEscenario
  roles: string[]
  total_injects: number
  total_tareas: number
}

export interface EscenarioDetalle extends EscenarioResumen {
  descripcion: string
  es_base: boolean
  injects: Inject[]
  tareas: Tarea[]
  pendientes_para_publicar: string[]
}

export interface TareaBanco extends Tarea {
  escenario_id: string
  escenario_nombre: string
  tipo_codigo: string
}

export interface InjectEntrada {
  id?: string
  titulo: string
  descripcion: string
  minuto_sugerido: number | null
}

export interface TareaEntrada {
  id?: string
  enunciado: string
  rol_codigo: string
  dificultad: Nivel
  criterios: string[]
  puntaje_maximo: number
  tiempo_limite_segundos: number
  respuesta_esperada: string | null
}

export interface EscenarioEntrada {
  nombre: string
  tipo_codigo: string
  descripcion: string
  nivel: Nivel
  roles: string[]
  injects: InjectEntrada[]
  tareas: TareaEntrada[]
}

export function consulta(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams()
  for (const [clave, valor] of Object.entries(params)) {
    if (valor) q.set(clave, valor)
  }
  const texto = q.toString()
  return texto ? `?${texto}` : ''
}

export const rutas = {
  tipos: '/catalogos/tipos-escenario',
  roles: '/catalogos/roles-ejercicio',
  escenarios: (filtros: Record<string, string | undefined>) =>
    `/escenarios${consulta(filtros)}`,
  escenario: (id: string) => `/escenarios/${id}`,
  banco: (filtros: Record<string, string | undefined>) =>
    `/banco-preguntas${consulta(filtros)}`,
}

export const crearEscenario = (datos: EscenarioEntrada) =>
  api<EscenarioDetalle>('/escenarios', { metodo: 'POST', cuerpo: datos })

export const actualizarEscenario = (id: string, datos: EscenarioEntrada) =>
  api<EscenarioDetalle>(`/escenarios/${id}`, { metodo: 'PUT', cuerpo: datos })

export const publicarEscenario = (id: string) =>
  api<EscenarioDetalle>(`/escenarios/${id}/publicar`, { metodo: 'POST' })

export const archivarEscenario = (id: string) =>
  api<EscenarioDetalle>(`/escenarios/${id}/archivar`, { metodo: 'POST' })
