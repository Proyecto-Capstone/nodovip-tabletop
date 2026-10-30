import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  OBSERVADOR,
  PARTICIPANTE,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { LeaderboardPage } from './LeaderboardPage'

function rutas() {
  return (
    <Routes>
      <Route path="/leaderboard" element={<LeaderboardPage />} />
    </Routes>
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const SESIONES = [
  {
    id: 's1',
    nombre: 'Simulacro Q4',
    estado: 'en_curso',
    total_injects: 3,
    inject_actual: 1,
    iniciada_en: '2026-01-10T09:00:00Z',
    finalizada_en: null,
  },
  {
    id: 's2',
    nombre: 'Simulacro Q3',
    estado: 'finalizada',
    total_injects: 2,
    inject_actual: 2,
    iniciada_en: '2025-12-01T09:00:00Z',
    finalizada_en: '2025-12-01T10:00:00Z',
  },
]

describe('LeaderboardPage', () => {
  it('muestra las sesiones visibles con su estado', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(200, SESIONES)))
    renderConSesion(rutas(), { sesion: sesionDePrueba(OBSERVADOR), ruta: '/leaderboard' })

    expect(await screen.findByText('Simulacro Q4')).toBeInTheDocument()
    expect(screen.getByText('Simulacro Q3')).toBeInTheDocument()
    expect(screen.getByText('En curso')).toBeInTheDocument()
    expect(screen.getByText('Finalizada')).toBeInTheDocument()
    expect(screen.getByText('● EN VIVO')).toBeInTheDocument()
    expect(screen.getByText('Inject 1/3')).toBeInTheDocument()
  })

  it('sin sesiones muestra un aviso', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(200, [])))
    renderConSesion(rutas(), { sesion: sesionDePrueba(OBSERVADOR), ruta: '/leaderboard' })

    expect(
      await screen.findByText(/No hay sesiones en curso ni finalizadas/),
    ).toBeInTheDocument()
  })

  it('un error del servidor se muestra', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuesta(500, { detail: 'Error interno del servidor' })),
    )
    renderConSesion(rutas(), { sesion: sesionDePrueba(OBSERVADOR), ruta: '/leaderboard' })

    expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor')
  })

  it('sin el permiso leaderboard:ver no se muestra la página', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE), ruta: '/leaderboard' })
    expect(screen.getByText(/Sin acceso/)).toBeInTheDocument()
  })
})
