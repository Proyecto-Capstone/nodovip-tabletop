import { describe, expect, it, vi } from 'vitest'
import { respuesta } from '../test/utilidades'
import { api, ApiError, avisarAlPerderSesion } from './client'

describe('cliente de la API', () => {
  it('no envía X-Rol-Debug y deja que el navegador mande la cookie', async () => {
    const fetchFalso = vi.fn(async () => respuesta(200, { ok: true }))
    vi.stubGlobal('fetch', fetchFalso)

    await api('/escenarios')

    const [url, opciones] = fetchFalso.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/escenarios')
    expect(opciones.credentials).toBe('same-origin')
    expect(JSON.stringify(opciones.headers ?? {})).not.toContain('X-Rol-Debug')
  })

  it('avisa que se perdió la sesión ante un 401', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(401, { detail: 'No autenticado' })))
    const aviso = vi.fn()
    const dejar = avisarAlPerderSesion(aviso)

    await expect(api('/usuarios')).rejects.toBeInstanceOf(ApiError)
    expect(aviso).toHaveBeenCalledTimes(1)
    dejar()
  })

  it('un login fallido no cuenta como sesión perdida', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuesta(401, { detail: 'Correo o contraseña incorrectos' })),
    )
    const aviso = vi.fn()
    const dejar = avisarAlPerderSesion(aviso)

    const error = await api('/auth/login', { metodo: 'POST', cuerpo: {} }).catch(
      (e: unknown) => e,
    )
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).errores).toEqual(['Correo o contraseña incorrectos'])
    expect(aviso).not.toHaveBeenCalled()
    dejar()
  })
})
