import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Usuario } from '../api/usuarios'
import {
  ADMINISTRADOR,
  MODERADOR,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { UsuariosPage } from './UsuariosPage'

const ACTIVO: Usuario = {
  id: 'ffffffff-0000-0000-0000-000000000001',
  nombre: 'Pedro Participante',
  correo: 'pedro@example.com',
  rol: 'participante',
  activo: true,
  creado_en: '2026-01-10T09:00:00Z',
}

const INACTIVO: Usuario = { ...ACTIVO, id: 'ffffffff-0000-0000-0000-000000000002', activo: false }

function abrir(lista: Usuario[] = [ACTIVO], usuario = ADMINISTRADOR) {
  const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST' && url.endsWith('/desactivar')) {
      return respuesta(200, { ...ACTIVO, activo: false })
    }
    if (init?.method === 'DELETE') return respuesta(204)
    if (init?.method === 'PUT') {
      return respuesta(200, { ...ACTIVO, ...JSON.parse(String(init.body)) })
    }
    return respuesta(200, lista)
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/usuarios" element={<UsuariosPage />} />
    </Routes>,
    { sesion: sesionDePrueba(usuario), ruta: '/usuarios' },
  )
  return fetchFalso
}

describe('UsuariosPage', () => {
  it('sin permiso de gestión muestra el aviso', () => {
    abrir([ACTIVO], MODERADOR)
    expect(screen.getByRole('alert')).toHaveTextContent('Sin acceso')
  })

  it('desactivar pide confirmación y, al confirmar, llama al backend', async () => {
    const fetchFalso = abrir([ACTIVO])
    await screen.findByText('Pedro Participante')

    await userEvent.click(screen.getByRole('button', { name: 'Desactivar' }))
    const dialogo = await screen.findByRole('alertdialog')
    expect(dialogo).toHaveTextContent('¿Desactivar a Pedro Participante?')

    await userEvent.click(within(dialogo).getByRole('button', { name: 'Desactivar' }))

    expect(await screen.findByText('Pedro Participante desactivado.')).toBeInTheDocument()
    expect(
      fetchFalso.mock.calls.some(
        ([url, init]) => url === `/api/usuarios/${ACTIVO.id}/desactivar` && init?.method === 'POST',
      ),
    ).toBe(true)
  })

  it('cancelar la confirmación de desactivar no llama al backend', async () => {
    const fetchFalso = abrir([ACTIVO])
    await screen.findByText('Pedro Participante')

    await userEvent.click(screen.getByRole('button', { name: 'Desactivar' }))
    await screen.findByRole('alertdialog')
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(fetchFalso.mock.calls.some(([url]) => String(url).endsWith('/desactivar'))).toBe(false)
  })

  it('un usuario inactivo puede eliminarse tras confirmar, con aviso de que no se puede deshacer', async () => {
    const fetchFalso = abrir([INACTIVO])
    await screen.findByText('Pedro Participante')

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar' }))
    const dialogo = await screen.findByRole('alertdialog')
    expect(dialogo).toHaveTextContent('¿Eliminar definitivamente a Pedro Participante?')
    expect(dialogo).toHaveTextContent('Correo pedro@example.com. Esta acción no se puede deshacer.')

    await userEvent.click(within(dialogo).getByRole('button', { name: 'Eliminar' }))

    expect(
      fetchFalso.mock.calls.some(
        ([url, init]) => url === `/api/usuarios/${INACTIVO.id}` && init?.method === 'DELETE',
      ),
    ).toBe(true)
  })

  it('agrupa a los usuarios en columnas por categoría de rol', async () => {
    abrir([ACTIVO, { ...ACTIVO, id: 'm1', nombre: 'Mónica Moderadora', rol: 'moderador' }])
    const participantes = await screen.findByRole('region', { name: 'Participantes' })
    expect(within(participantes).getByText('Pedro Participante')).toBeInTheDocument()
    const moderacion = screen.getByRole('region', { name: 'Moderación y análisis' })
    expect(within(moderacion).getByText('Mónica Moderadora')).toBeInTheDocument()
  })

  it('cambia el rol desde la tarjeta tras confirmar', async () => {
    const fetchFalso = abrir()
    await userEvent.selectOptions(
      await screen.findByLabelText('Rol de Pedro Participante'),
      'analista',
    )
    const dialogo = await screen.findByRole('alertdialog')
    expect(dialogo).toHaveTextContent('Pasará de Participante a Analista')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cambiar rol' }))

    expect(await screen.findByText('Pedro Participante ahora es Analista.')).toBeInTheDocument()
    const put = fetchFalso.mock.calls.find(([, init]) => init?.method === 'PUT')
    expect(put?.[0]).toBe(`/api/usuarios/${ACTIVO.id}`)
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({
      nombre: ACTIVO.nombre,
      correo: ACTIVO.correo,
      rol: 'analista',
    })
  })

  it('no permite cambiarse el rol ni desactivarse a uno mismo', async () => {
    abrir([{ ...ACTIVO, id: ADMINISTRADOR.id, nombre: 'Yo Mismo', rol: 'administrador' }])
    expect(await screen.findByLabelText('Rol de Yo Mismo')).toBeDisabled()
    expect(screen.getByText('Tú')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Desactivar' })).not.toBeInTheDocument()
  })
})
