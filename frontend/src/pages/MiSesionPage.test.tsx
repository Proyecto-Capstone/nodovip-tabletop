import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { MiSesion } from '../api/misSesiones'
import {
  MODERADOR,
  PARTICIPANTE,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { MiSesionPage } from './MiSesionPage'
import { MisSesionesPage } from './MisSesionesPage'

const SESION: MiSesion = {
  id: 'cccccccc-0000-0000-0000-000000000001',
  nombre: 'Simulacro Q4',
  estado: 'programada',
  fecha_programada: '2026-10-27T14:00:00Z',
  duracion_minutos: 90,
  escenario_nombre: 'Ransomware en servidores de archivos',
  escenario_descripcion: 'Cifrado masivo de los servidores.',
  moderador_nombre: 'Mónica Moderadora',
  rol_codigo: 'legal',
  rol_nombre: 'Legal',
  total_participantes: 5,
  invitacion: 'enviada',
  invitacion_aceptada_en: null,
}

function abrir(ruta: string, usuario = PARTICIPANTE) {
  renderConSesion(
    <Routes>
      <Route path="/mis-sesiones" element={<MisSesionesPage />} />
      <Route path="/mis-sesiones/:id" element={<MiSesionPage />} />
    </Routes>,
    { sesion: sesionDePrueba(usuario), ruta },
  )
}

describe('Vista del participante', () => {
  it('lista sus sesiones con su rol y el estado de la invitación', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(200, [SESION])))
    abrir('/mis-sesiones')

    expect(await screen.findByRole('heading', { name: 'Simulacro Q4' })).toBeInTheDocument()
    expect(screen.getByText('Legal')).toBeInTheDocument()
    expect(screen.getByText('Enviada')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Simulacro Q4/ })).toHaveAttribute(
      'href',
      `/mis-sesiones/${SESION.id}`,
    )
  })

  it('muestra su rol y confirma la asistencia', async () => {
    const fetchFalso = vi.fn(async (_url: string, init?: RequestInit) =>
      init?.method === 'POST'
        ? respuesta(200, { ...SESION, invitacion: 'aceptada', invitacion_aceptada_en: '2026-10-25T15:00:00Z' })
        : respuesta(200, SESION),
    )
    vi.stubGlobal('fetch', fetchFalso)
    abrir(`/mis-sesiones/${SESION.id}`)

    expect(await screen.findByText('Tu rol en este ejercicio')).toBeInTheDocument()
    expect(screen.getByText('Legal')).toBeInTheDocument()
    expect(screen.getByText('Mónica Moderadora')).toBeInTheDocument()
    expect(screen.getByText('1 h 30 min')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar asistencia' }))

    expect(await screen.findByText(/Confirmaste tu asistencia/)).toBeInTheDocument()
    expect(screen.getByText('Aceptada')).toBeInTheDocument()
    expect(fetchFalso).toHaveBeenCalledWith(
      `/api/mis-sesiones/${SESION.id}/aceptar`,
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('una sesión a la que no fue invitado muestra un aviso', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(404, { detail: 'Sesión no encontrada' })))
    abrir(`/mis-sesiones/${SESION.id}`)

    expect(await screen.findByText(/No encontramos esta sesión/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar asistencia' })).toBeNull()
  })

  it('sin permiso de participante muestra el aviso', () => {
    vi.stubGlobal('fetch', vi.fn())
    abrir('/mis-sesiones', MODERADOR)
    expect(screen.getByRole('alert')).toHaveTextContent('Sin acceso')
  })
})
