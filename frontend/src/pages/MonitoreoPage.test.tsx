import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ResumenMonitoreo } from '../api/monitoreo'
import { ADMINISTRADOR, PARTICIPANTE, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { MonitoreoPage } from './MonitoreoPage'

function rutas() {
  return (
    <Routes>
      <Route path="/monitoreo" element={<MonitoreoPage />} />
    </Routes>
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

const RESUMEN: ResumenMonitoreo = {
  activas: 1,
  maximo: 10,
  sesiones: [
    {
      id: 's1',
      nombre: 'Simulacro Q4',
      moderador_nombre: 'Mónica Moderadora',
      escenario_nombre: 'Ransomware',
      pausada: false,
      invitados: 5,
      conectados: 3,
      inject_actual: 1,
      total_injects: 3,
      respuestas_recibidas: 2,
      respuestas_esperadas: 5,
      porcentaje_avance: 40,
      segundos_transcurridos: 90,
      iniciada_en: '2026-01-10T09:00:00Z',
      duracion_minutos: 60,
      excede_duracion: false,
    },
  ],
}

describe('MonitoreoPage', () => {
  it('sin el permiso sesiones:monitorear no se muestra la página', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE), ruta: '/monitoreo' })
    expect(screen.getByText(/Sin acceso/)).toBeInTheDocument()
  })

  it('muestra el cupo y las sesiones activas con enlace a modo lectura', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(200, RESUMEN)))
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/monitoreo' })

    expect(await screen.findByText('1 de 10 sesiones activas')).toBeInTheDocument()
    expect(screen.getByText('Simulacro Q4')).toBeInTheDocument()
    expect(screen.getByText('Moderador: Mónica Moderadora')).toBeInTheDocument()
    expect(screen.getByText('3/5')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver en modo lectura' })).toHaveAttribute(
      'href',
      '/monitoreo/s1',
    )
    expect(screen.queryByText(/Excede la duración/)).not.toBeInTheDocument()
  })

  it('sin sesiones activas muestra un aviso', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(200, { ...RESUMEN, activas: 0, sesiones: [] })))
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/monitoreo' })

    expect(await screen.findByText('No hay sesiones activas.')).toBeInTheDocument()
  })

  it('con el cupo lleno marca la barra de avance como llena', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuesta(200, { ...RESUMEN, activas: 10, maximo: 10 })),
    )
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/monitoreo' })

    expect(await screen.findByText('10 de 10 sesiones activas')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Cupo de sesiones activas' })).toHaveClass(
      'cupo-lleno',
    )
  })

  it('marca con un badge las sesiones que exceden su duración programada', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        respuesta(200, {
          ...RESUMEN,
          sesiones: [{ ...RESUMEN.sesiones[0], excede_duracion: true, duracion_minutos: 60 }],
        }),
      ),
    )
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/monitoreo' })

    expect(await screen.findByText(/Excede la duración:.*de 60 min/)).toBeInTheDocument()
  })

  it('un error del servidor se muestra', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuesta(500, { detail: 'Error interno del servidor' })),
    )
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/monitoreo' })

    expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor')
  })
})
