// Tipos y llamadas de gestión de usuarios (PB-02).

import { api, type RolSistema } from './client'
import { consulta } from './escenarios'

export interface Usuario {
  id: string
  nombre: string
  correo: string
  rol: RolSistema
  activo: boolean
  creado_en: string | null
}

export interface UsuarioCrear {
  nombre: string
  correo: string
  contrasena: string
  rol: RolSistema
}

export interface UsuarioActualizar {
  nombre: string
  correo: string
  rol: RolSistema
}

export const rutaUsuarios = (filtros: Record<string, string | undefined>) =>
  `/usuarios${consulta(filtros)}`

export const crearUsuario = (datos: UsuarioCrear) =>
  api<Usuario>('/usuarios', { metodo: 'POST', cuerpo: datos })

export const actualizarUsuario = (id: string, datos: UsuarioActualizar) =>
  api<Usuario>(`/usuarios/${id}`, { metodo: 'PUT', cuerpo: datos })

export const desactivarUsuario = (id: string) =>
  api<Usuario>(`/usuarios/${id}/desactivar`, { metodo: 'POST' })

export const activarUsuario = (id: string) =>
  api<Usuario>(`/usuarios/${id}/activar`, { metodo: 'POST' })

export const restablecerContrasena = (id: string, contrasena: string) =>
  api<Usuario>(`/usuarios/${id}/contrasena`, {
    metodo: 'POST',
    cuerpo: { contrasena },
  })

// Borrado definitivo: el backend solo lo permite con cuentas desactivadas.
export const eliminarUsuario = (id: string) =>
  api<null>(`/usuarios/${id}`, { metodo: 'DELETE' })
