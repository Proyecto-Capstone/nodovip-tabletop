// Estado y reglas compartidas por los pasos del diseñador de tabletop (PB-05).

import type { RolEjercicio } from '../../api/escenarios'
import type {
  ParticipanteDisponible,
  SesionDiseno,
  TareaSesion,
} from '../../api/sesiones'

export interface PropsPaso {
  d: SesionDiseno
  cambiar: (cambio: (d: SesionDiseno) => SesionDiseno) => void
  roles: RolEjercicio[]
  disponibles: ParticipanteDisponible[]
}

export const PASOS = [
  'Seleccionar escenario',
  'Configurar roles',
  'Asignar tareas e injects',
  'Criterios de puntuación',
  'Programar sesión',
  'Enviar invitaciones',
] as const

export const ETIQUETA_TIPO_TAREA = {
  texto_libre: 'Texto libre',
  seleccion_multiple: 'Selección múltiple',
} as const

export const nuevoId = () => crypto.randomUUID()

export function tareaNueva(rol: string, inject_id: string | null): TareaSesion {
  return {
    id: nuevoId(),
    inject_id,
    rol_codigo: rol,
    tipo: 'texto_libre',
    enunciado: '',
    opciones: [],
    criterios: [],
    dificultad: 'medio',
    puntaje_maximo: 10,
    tiempo_limite_segundos: 300,
    respuesta_esperada: null,
  }
}

export function participanteDe(d: SesionDiseno, rol: string) {
  return d.participantes.find((p) => p.rol_codigo === rol)?.usuario_id ?? ''
}

export function tareaCompleta(t: TareaSesion) {
  if (t.enunciado.trim().length < 10 || !t.inject_id) return false
  if (t.tipo === 'seleccion_multiple') {
    return t.opciones.length >= 2 && t.opciones.some((o) => o.correcta)
  }
  return t.criterios.some((c) => c.trim())
}

export const sumaPesos = (d: SesionDiseno) =>
  d.pesos.completitud + d.pesos.precision + d.pesos.tiempo

/** Qué pasos (2 a 5) ya cumplen sus reglas, para marcarlos con ✓. */
export function pasosCompletos(d: SesionDiseno, ahora = new Date()): boolean[] {
  const rolesCubiertos = d.roles.every((r) => participanteDe(d, r))
  const tareasOk =
    d.injects.length > 0 &&
    d.roles.every((r) => d.tareas.some((t) => t.rol_codigo === r)) &&
    d.tareas.every(tareaCompleta)
  const fechaOk =
    d.fecha_programada !== null && new Date(d.fecha_programada) > ahora
  return [
    true,
    d.roles.length > 0 && rolesCubiertos,
    d.roles.length > 0 && tareasOk,
    sumaPesos(d) === 100,
    fechaOk && Boolean(d.duracion_minutos),
    false,
  ]
}

/** Quita líneas vacías antes de enviar (el textarea las necesita al escribir). */
export function limpiarDiseno(d: SesionDiseno): SesionDiseno {
  return {
    ...d,
    nombre: d.nombre.trim(),
    tareas: d.tareas.map((t) => ({
      ...t,
      criterios: t.criterios.map((c) => c.trim()).filter(Boolean),
      opciones: t.tipo === 'seleccion_multiple' ? t.opciones : [],
      respuesta_esperada: t.respuesta_esperada?.trim() || null,
    })),
  }
}

/** ISO (UTC) → valor de <input type="datetime-local"> en la hora local. */
export function aFechaLocal(iso: string | null) {
  if (!iso) return ''
  const f = new Date(iso)
  const dos = (n: number) => String(n).padStart(2, '0')
  return (
    `${f.getFullYear()}-${dos(f.getMonth() + 1)}-${dos(f.getDate())}` +
    `T${dos(f.getHours())}:${dos(f.getMinutes())}`
  )
}

export const desdeFechaLocal = (valor: string) =>
  valor ? new Date(valor).toISOString() : null

export function formatoFecha(iso: string | null) {
  if (!iso) return 'sin fecha'
  return new Date(iso).toLocaleString('es-EC', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatoDuracion(minutos: number) {
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  if (!horas) return `${resto} min`
  return resto ? `${horas} h ${resto} min` : `${horas} h`
}
