// Inicio y cierre de sesión (PB-01). La cookie de sesión la pone y la borra el
// backend; aquí solo se recibe el usuario con sus permisos.

import { api, type RolSistema } from './client'

export type Permiso =
  | 'usuarios:gestionar'
  | 'escenarios:gestionar'
  | 'escenarios:leer'
  | 'sesiones:disenar'
  | 'sesiones:conducir'
  | 'sesiones:participar'
  | 'sesiones:monitorear'
  | 'leaderboard:ver'
  | 'reportes:generar'
  | 'reportes:ver'

export interface Sesion {
  id: string
  nombre: string
  correo: string
  rol: RolSistema
  permisos: Permiso[]
}

export const iniciarSesion = (correo: string, contrasena: string) =>
  api<Sesion>('/auth/login', { metodo: 'POST', cuerpo: { correo, contrasena } })

export const cerrarSesion = () => api<null>('/auth/logout', { metodo: 'POST' })

export const obtenerSesion = () => api<Sesion>('/auth/yo')
