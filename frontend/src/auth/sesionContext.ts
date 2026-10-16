import { createContext, useContext } from 'react'
import type { Permiso, Sesion } from '../api/auth'
import type { RolSistema } from '../api/client'

export interface SesionContextValor {
  usuario: Sesion | null
  /** true mientras se consulta /auth/yo al abrir la aplicación. */
  cargando: boolean
  iniciarSesion: (correo: string, contrasena: string) => Promise<Sesion>
  cerrarSesion: () => Promise<void>
  puede: (permiso: Permiso) => boolean
  /** Rol del usuario o '' sin sesión. Sirve de clave para recargar datos. */
  rol: RolSistema | ''
  puedeLeerEscenarios: boolean
  puedeGestionarEscenarios: boolean
  puedeGestionarUsuarios: boolean
}

export const SesionContext = createContext<SesionContextValor | null>(null)

export function useSesion(): SesionContextValor {
  const valor = useContext(SesionContext)
  if (!valor) throw new Error('useSesion debe usarse dentro de SesionProvider')
  return valor
}

/** Valor del contexto a partir del usuario; también lo usan las pruebas. */
export function valorSesion(
  usuario: Sesion | null,
  acciones: Pick<SesionContextValor, 'cargando' | 'iniciarSesion' | 'cerrarSesion'>,
): SesionContextValor {
  const puede = (permiso: Permiso) => usuario?.permisos.includes(permiso) ?? false
  return {
    ...acciones,
    usuario,
    puede,
    rol: usuario?.rol ?? '',
    puedeLeerEscenarios: puede('escenarios:leer'),
    puedeGestionarEscenarios: puede('escenarios:gestionar'),
    puedeGestionarUsuarios: puede('usuarios:gestionar'),
  }
}

export const ROLES_SISTEMA: { codigo: RolSistema; nombre: string }[] = [
  { codigo: 'administrador', nombre: 'Administrador' },
  { codigo: 'moderador', nombre: 'Moderador' },
  { codigo: 'participante', nombre: 'Participante' },
  { codigo: 'observador', nombre: 'Observador' },
  { codigo: 'analista', nombre: 'Analista' },
]

export const nombreRolSistema = (rol: RolSistema) =>
  ROLES_SISTEMA.find((r) => r.codigo === rol)?.nombre ?? rol
