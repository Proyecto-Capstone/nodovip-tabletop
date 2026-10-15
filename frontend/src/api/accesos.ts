// Historial de accesos (PB-01, RNF-01). Solo Administrador.

import { consulta } from './escenarios'

export type ResultadoAcceso =
  | 'exitoso'
  | 'credenciales_invalidas'
  | 'usuario_inactivo'
  | 'bloqueado'

export interface Acceso {
  id: number
  fecha_hora: string | null
  correo: string
  usuario_id: string | null
  ip: string
  user_agent: string | null
  resultado: ResultadoAcceso
}

export const rutaAccesos = (filtros: Record<string, string | undefined>) =>
  `/accesos${consulta(filtros)}`
