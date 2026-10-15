import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import {
  ADMINISTRADOR,
  PARTICIPANTE,
  renderConSesion,
  sesionDePrueba,
} from '../test/utilidades'
import { Layout } from './Layout'

function rutas() {
  return (
    <Routes>
      <Route path="/login" element={<p>Pantalla de login</p>} />
      <Route element={<Layout />}>
        <Route path="/" element={<p>Inicio</p>} />
      </Route>
    </Routes>
  )
}

describe('Layout', () => {
  it('muestra el usuario y el menú según sus permisos', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    expect(screen.getByText('Ana Admin')).toBeInTheDocument()
    expect(screen.getByText('Administrador')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Gestión de usuarios' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Historial de accesos' })).toBeInTheDocument()
    // Ya no existe el selector de rol de desarrollo.
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('un participante no ve la biblioteca ni la administración', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE) })
    expect(screen.queryByRole('link', { name: 'Biblioteca de escenarios' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Gestión de usuarios' })).toBeNull()
  })

  it('cerrar sesión llama al backend y vuelve al login', async () => {
    const sesion = sesionDePrueba(ADMINISTRADOR)
    renderConSesion(rutas(), { sesion })
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(sesion.cerrarSesion).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('Pantalla de login')).toBeInTheDocument()
  })
})
