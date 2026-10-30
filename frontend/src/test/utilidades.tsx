// Utilidades para probar pantallas con una sesión simulada (sin backend).

import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, type InitialEntry } from 'react-router-dom'
import { vi } from 'vitest'
import type { Sesion } from '../api/auth'
import { SesionContext, valorSesion, type SesionContextValor } from '../auth/sesionContext'

export const ADMINISTRADOR: Sesion = {
  id: '11111111-1111-1111-1111-111111111111',
  nombre: 'Ana Admin',
  correo: 'ana@example.com',
  rol: 'administrador',
  permisos: [
    'escenarios:gestionar',
    'escenarios:leer',
    'leaderboard:ver',
    'reportes:ver',
    'sesiones:monitorear',
    'usuarios:gestionar',
  ],
}

export const MODERADOR: Sesion = {
  id: '33333333-3333-3333-3333-333333333333',
  nombre: 'Mónica Moderadora',
  correo: 'monica@example.com',
  rol: 'moderador',
  permisos: [
    'escenarios:leer',
    'leaderboard:ver',
    'reportes:ver',
    'sesiones:conducir',
    'sesiones:disenar',
  ],
}

export const OBSERVADOR: Sesion = {
  id: '44444444-4444-4444-4444-444444444444',
  nombre: 'Olga Observadora',
  correo: 'olga@example.com',
  rol: 'observador',
  permisos: ['leaderboard:ver'],
}

export const PARTICIPANTE: Sesion = {
  id: '22222222-2222-2222-2222-222222222222',
  nombre: 'Pedro Participante',
  correo: 'pedro@example.com',
  rol: 'participante',
  permisos: ['sesiones:participar'],
}

export function sesionDePrueba(
  usuario: Sesion | null,
  cambios: Partial<SesionContextValor> = {},
): SesionContextValor {
  return {
    ...valorSesion(usuario, {
      cargando: false,
      iniciarSesion: vi.fn(async () => usuario as Sesion),
      cerrarSesion: vi.fn(async () => {}),
    }),
    ...cambios,
  }
}

export function renderConSesion(
  ui: ReactNode,
  { sesion, ruta = '/' }: { sesion: SesionContextValor; ruta?: InitialEntry },
) {
  return render(
    <SesionContext.Provider value={sesion}>
      <MemoryRouter initialEntries={[ruta]}>{ui}</MemoryRouter>
    </SesionContext.Provider>,
  )
}

/** Respuesta JSON para simular fetch. */
export function respuesta(status: number, cuerpo?: unknown) {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
