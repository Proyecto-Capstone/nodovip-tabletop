import type { ResultadoAcceso } from '../api/accesos'
import type { EstadoEscenario, Nivel, RolEjercicio, TipoEscenario } from '../api/escenarios'

export const NIVELES: Nivel[] = ['bajo', 'medio', 'alto']

export const ETIQUETA_NIVEL: Record<Nivel, string> = {
  bajo: 'Bajo',
  medio: 'Medio',
  alto: 'Alto',
}

export const ETIQUETA_ESTADO: Record<EstadoEscenario, string> = {
  borrador: 'Borrador',
  publicado: 'Publicado',
  archivado: 'Archivado',
}

export const ETIQUETA_RESULTADO: Record<ResultadoAcceso, string> = {
  exitoso: 'Exitoso',
  credenciales_invalidas: 'Credenciales inválidas',
  usuario_inactivo: 'Cuenta inactiva',
  bloqueado: 'Bloqueado',
}

export function nombreTipo(tipos: TipoEscenario[] | undefined, codigo: string) {
  return tipos?.find((t) => t.codigo === codigo)?.nombre ?? codigo
}

export function nombreRol(roles: RolEjercicio[] | undefined, codigo: string) {
  return roles?.find((r) => r.codigo === codigo)?.nombre ?? codigo
}

export function formatoTiempo(segundos: number) {
  const min = Math.floor(segundos / 60)
  const seg = segundos % 60
  return seg ? `${min} min ${seg} s` : `${min} min`
}
