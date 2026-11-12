import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { SesionResumen } from '../api/sesiones'
import { MODERADOR, PARTICIPANTE, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { SesionesPage } from './SesionesPage'

const BORRADOR: SesionResumen = {
  id: 'eeeeeeee-0000-0000-0000-000000000001',
  nombre: 'Ransomware Sector Financiero',
  cliente: null,
  escenario_id: 'dddddddd-0000-0000-0000-000000000001',
  estado: 'borrador',
  fecha_programada: null,
  duracion_minutos: null,
  roles: ['ti', 'legal'],
  total_participantes: 0,
  puntaje_maximo_total: 20,
}

function abrir(lista: SesionResumen[] = [BORRADOR], usuario = MODERADOR) {
  const fetchFalso = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'DELETE') return respuesta(204)
    return respuesta(200, lista)
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/sesiones" element={<SesionesPage />} />
    </Routes>,
    { sesion: sesionDePrueba(usuario), ruta: '/sesiones' },
  )
  return fetchFalso
}

describe('SesionesPage', () => {
  it('sin permiso de diseño muestra el aviso', () => {
    abrir([BORRADOR], PARTICIPANTE)
    expect(screen.getByRole('alert')).toHaveTextContent('Sin acceso')
  })

  it('lista los borradores y permite eliminar uno tras confirmar', async () => {
    const fetchFalso = abrir()
    expect(await screen.findByText('Ransomware Sector Financiero')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    const dialogo = await screen.findByRole('alertdialog')
    expect(dialogo).toHaveTextContent('¿Eliminar el borrador "Ransomware Sector Financiero"?')

    await userEvent.click(within(dialogo).getByRole('button', { name: 'Eliminar' }))

    expect(
      fetchFalso.mock.calls.some(
        ([url, init]) => url === `/api/sesiones/${BORRADOR.id}` && init?.method === 'DELETE',
      ),
    ).toBe(true)
  })

  it('cancelar la confirmación no elimina el borrador', async () => {
    const fetchFalso = abrir()
    await screen.findByText('Ransomware Sector Financiero')

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    await screen.findByRole('alertdialog')
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(
      fetchFalso.mock.calls.some(([, init]) => init?.method === 'DELETE'),
    ).toBe(false)
  })
})
