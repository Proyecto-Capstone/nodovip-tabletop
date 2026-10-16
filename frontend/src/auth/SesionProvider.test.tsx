import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import { ADMINISTRADOR, respuesta } from '../test/utilidades'
import { SesionProvider } from './SesionProvider'
import { useSesion } from './sesionContext'

function Estado() {
  const { usuario, cargando, cerrarSesion } = useSesion()
  if (cargando) return <p>cargando</p>
  return (
    <>
      <p>{usuario ? `sesión de ${usuario.nombre}` : 'sin sesión'}</p>
      <button type="button" onClick={() => cerrarSesion()}>
        salir
      </button>
    </>
  )
}

/** fetch falso que responde según "MÉTODO /ruta". */
function backend(rutas: Record<string, () => Response>) {
  const fetchFalso = vi.fn(async (url: string, opciones?: RequestInit) => {
    const clave = `${opciones?.method ?? 'GET'} ${url}`
    const responder = rutas[clave]
    if (!responder) throw new Error(`Ruta no simulada: ${clave}`)
    return responder()
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

describe('SesionProvider', () => {
  it('al abrir recupera la sesión desde /auth/yo', async () => {
    backend({ 'GET /api/auth/yo': () => respuesta(200, ADMINISTRADOR) })
    render(<SesionProvider><Estado /></SesionProvider>)
    expect(screen.getByText('cargando')).toBeInTheDocument()
    expect(await screen.findByText('sesión de Ana Admin')).toBeInTheDocument()
  })

  it('sin cookie válida queda sin sesión', async () => {
    backend({ 'GET /api/auth/yo': () => respuesta(401, { detail: 'No autenticado' }) })
    render(<SesionProvider><Estado /></SesionProvider>)
    expect(await screen.findByText('sin sesión')).toBeInTheDocument()
  })

  it('si otra llamada recibe 401 (sesión vencida) se cierra la sesión local', async () => {
    backend({
      'GET /api/auth/yo': () => respuesta(200, ADMINISTRADOR),
      'GET /api/usuarios': () => respuesta(401, { detail: 'No autenticado' }),
    })
    render(<SesionProvider><Estado /></SesionProvider>)
    await screen.findByText('sesión de Ana Admin')

    await act(() => api('/usuarios').catch(() => undefined))
    expect(screen.getByText('sin sesión')).toBeInTheDocument()
  })

  it('cerrar sesión llama a /auth/logout aunque falle la red', async () => {
    const fetchFalso = backend({
      'GET /api/auth/yo': () => respuesta(200, ADMINISTRADOR),
      'POST /api/auth/logout': () => {
        throw new TypeError('Failed to fetch')
      },
    })
    render(<SesionProvider><Estado /></SesionProvider>)
    await screen.findByText('sesión de Ana Admin')

    await userEvent.click(screen.getByRole('button', { name: 'salir' }))
    await waitFor(() => expect(screen.getByText('sin sesión')).toBeInTheDocument())
    expect(fetchFalso).toHaveBeenCalledWith('/api/auth/logout', expect.anything())
  })
})
