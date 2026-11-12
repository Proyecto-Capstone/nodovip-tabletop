import { cleanup, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import {
  ADMINISTRADOR,
  ANALISTA,
  OBSERVADOR,
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
        <Route path="/escenarios" element={<p>Biblioteca</p>} />
        <Route
          path="/escenarios/:id"
          element={
            <>
              <p>Detalle</p>
              <Link to="/escenarios">Volver</Link>
            </>
          }
        />
      </Route>
    </Routes>
  )
}

beforeEach(() => {
  localStorage.clear()
})

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

  it('el observador ve la opción de leaderboard', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(OBSERVADOR) })
    expect(screen.getByRole('link', { name: 'Leaderboard' })).toBeInTheDocument()
  })

  it('un participante no ve la opción de leaderboard (sin el permiso)', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE) })
    expect(screen.queryByRole('link', { name: 'Leaderboard' })).toBeNull()
  })

  it('el administrador ve la opción de monitoreo', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    expect(screen.getByRole('link', { name: 'Monitoreo' })).toBeInTheDocument()
  })

  it('un participante no ve la opción de monitoreo (sin el permiso)', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE) })
    expect(screen.queryByRole('link', { name: 'Monitoreo' })).toBeNull()
  })

  it('la analista ve la opción de reportes y el participante no', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ANALISTA) })
    expect(screen.getByRole('link', { name: 'Reportes' })).toBeInTheDocument()
    cleanup()
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE) })
    expect(screen.queryByRole('link', { name: 'Reportes' })).toBeNull()
  })

  it('cerrar sesión llama al backend y vuelve al login', async () => {
    const sesion = sesionDePrueba(ADMINISTRADOR)
    renderConSesion(rutas(), { sesion })
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(sesion.cerrarSesion).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('Pantalla de login')).toBeInTheDocument()
  })

  it('agrupa los enlaces del menú por función', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    expect(screen.getByText('Operación')).toBeInTheDocument()
    expect(screen.getByText('Diseño')).toBeInTheDocument()
    expect(screen.getByText('Análisis')).toBeInTheDocument()
    expect(screen.getByText('Administración')).toBeInTheDocument()
  })

  it('colapsa el menú, recuerda el estado en localStorage y lo restaura al volver a montar', async () => {
    const { unmount } = renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    await userEvent.click(screen.getByRole('button', { name: 'Colapsar' }))
    expect(localStorage.getItem('nodovip_sidebar_colapsado')).toBe('si')
    expect(screen.getByRole('button', { name: 'Expandir' })).toBeInTheDocument()
    unmount()

    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    expect(screen.getByRole('button', { name: 'Expandir' })).toBeInTheDocument()
  })

  it('abre y cierra el cajón móvil con la hamburguesa y con Escape', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    const hamburguesa = screen.getByRole('button', { name: 'Abrir menú' })
    await userEvent.click(hamburguesa)
    expect(screen.getByRole('button', { name: 'Cerrar menú' })).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('button', { name: 'Abrir menú' })).toBeInTheDocument()
  })

  it('cierra el cajón móvil al hacer clic fuera (el velo) y al navegar', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })
    await userEvent.click(screen.getByRole('button', { name: 'Abrir menú' }))
    const velo = document.querySelector('.velo-cajon')
    expect(velo).not.toBeNull()
    await userEvent.click(velo as Element)
    expect(screen.getByRole('button', { name: 'Abrir menú' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Abrir menú' }))
    await userEvent.click(screen.getAllByRole('link', { name: 'Biblioteca de escenarios' })[0])
    expect(screen.getByRole('button', { name: 'Abrir menú' })).toBeInTheDocument()
  })

  it('muestra migas de pan en páginas internas, no en las de primer nivel', () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(ADMINISTRADOR),
      ruta: '/escenarios',
    })
    expect(screen.queryByRole('navigation', { name: 'Ruta de navegación' })).toBeNull()
    cleanup()

    renderConSesion(rutas(), {
      sesion: sesionDePrueba(ADMINISTRADOR),
      ruta: '/escenarios/abc-123',
    })
    const migas = screen.getByRole('navigation', { name: 'Ruta de navegación' })
    expect(migas).toHaveTextContent('Diseño')
    expect(migas).toHaveTextContent('Detalle del escenario')
  })
})
