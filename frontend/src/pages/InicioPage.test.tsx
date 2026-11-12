import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  ADMINISTRADOR,
  ANALISTA,
  MODERADOR,
  OBSERVADOR,
  PARTICIPANTE,
  renderConSesion,
  sesionDePrueba,
} from '../test/utilidades'
import { InicioPage } from './InicioPage'

/** Textos visibles de los accesos directos, en orden. */
function accesosDe(usuario: typeof ADMINISTRADOR) {
  renderConSesion(<InicioPage />, { sesion: sesionDePrueba(usuario), ruta: '/' })
  const dock = screen.getByRole('navigation', { name: 'Accesos directos' })
  return within(dock)
    .getAllByRole('link')
    .map((enlace) => enlace.querySelector('.portada-acceso-texto')?.textContent)
}

describe('InicioPage', () => {
  it('saluda al usuario con su rol y muestra el logo', () => {
    renderConSesion(<InicioPage />, { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/' })
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Hola, /)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Administrador')
    expect(screen.getByRole('img', { name: /NODOVIP/ })).toBeInTheDocument()
  })

  it('el Administrador ve las secciones de diseño, análisis y administración', () => {
    expect(accesosDe(ADMINISTRADOR)).toEqual([
      'Escenarios',
      'Preguntas',
      'Nuevo',
      'Leaderboard',
      'Monitoreo',
      'Reportes',
      'Usuarios',
      'Accesos',
    ])
  })

  it('el Moderador ve sus tabletops y la biblioteca, sin administración', () => {
    const accesos = accesosDe(MODERADOR)
    expect(accesos).toContain('Tabletops')
    expect(accesos).toContain('Escenarios')
    expect(accesos).not.toContain('Usuarios')
    expect(accesos).not.toContain('Nuevo')
  })

  it('el Participante solo ve sus sesiones', () => {
    expect(accesosDe(PARTICIPANTE)).toEqual(['Mis sesiones'])
  })

  it('el Analista ve los reportes', () => {
    expect(accesosDe(ANALISTA)).toContain('Reportes')
  })

  it('el Observador ve el leaderboard', () => {
    expect(accesosDe(OBSERVADOR)).toContain('Leaderboard')
  })

  it('los accesos llevan a la sección completa con su nombre accesible', () => {
    renderConSesion(<InicioPage />, { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/' })
    expect(screen.getByRole('link', { name: /Biblioteca de escenarios/ })).toHaveAttribute(
      'href',
      '/escenarios',
    )
  })
})
