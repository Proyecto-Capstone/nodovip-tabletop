import { screen } from '@testing-library/react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import {
  ADMINISTRADOR,
  PARTICIPANTE,
  renderConSesion,
  sesionDePrueba,
} from '../test/utilidades'
import { RutaProtegida } from './RutaProtegida'

function LoginFalso() {
  const { state } = useLocation()
  return <p>Login (volver a {(state as { desde?: string } | null)?.desde})</p>
}

function rutas() {
  return (
    <Routes>
      <Route path="/login" element={<LoginFalso />} />
      <Route element={<RutaProtegida />}>
        <Route path="/escenarios" element={<p>Biblioteca</p>} />
        <Route element={<RutaProtegida permiso="usuarios:gestionar" />}>
          <Route path="/usuarios" element={<p>Gestión de usuarios</p>} />
        </Route>
      </Route>
    </Routes>
  )
}

describe('RutaProtegida', () => {
  it('mientras se consulta la sesión muestra "Cargando…"', () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(null, { cargando: true }),
      ruta: '/escenarios',
    })
    expect(screen.getByRole('status')).toHaveTextContent('Cargando')
  })

  it('sin sesión redirige al login recordando la ruta', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(null), ruta: '/escenarios?q=ransom' })
    expect(screen.getByText('Login (volver a /escenarios?q=ransom)')).toBeInTheDocument()
  })

  it('con sesión muestra la página', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/usuarios' })
    expect(screen.getByText('Gestión de usuarios')).toBeInTheDocument()
  })

  it('sin el permiso muestra "Sin acceso"', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE), ruta: '/usuarios' })
    expect(screen.getByRole('alert')).toHaveTextContent('Sin acceso')
    expect(screen.queryByText('Gestión de usuarios')).not.toBeInTheDocument()
  })
})
