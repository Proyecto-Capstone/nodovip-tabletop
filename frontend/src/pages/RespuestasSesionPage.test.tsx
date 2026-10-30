import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { RespuestaRegistrada } from '../api/respuestas'
import { MODERADOR, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { RespuestasSesionPage } from './RespuestasSesionPage'

const ID = 'dddddddd-0000-0000-0000-000000000001'

const BASE: RespuestaRegistrada = {
  id: 'r1',
  recibida_en: '2026-11-02T14:03:05Z',
  segundos_usados: 65,
  participante_id: 'u1',
  participante_nombre: 'Ana López',
  participante_correo: 'ana.lopez@demo.nodovip.test',
  rol_codigo: 'ciso',
  rol_nombre: 'CISO',
  inject_orden: 1,
  inject_titulo: 'Detección',
  tarea_id: 't1',
  tarea_enunciado: '¿Aísla los servidores?',
  tipo: 'texto_libre',
  tiempo_limite_segundos: 300,
  texto: 'Aíslo el file server',
  opciones_elegidas: [],
  opciones_elegidas_texto: [],
}

const OPCIONES: RespuestaRegistrada = {
  ...BASE,
  id: 'r2',
  participante_nombre: 'Carlos Ramírez',
  rol_codigo: 'legal',
  rol_nombre: 'Legal',
  inject_orden: 2,
  inject_titulo: 'Extorsión',
  tarea_enunciado: '¿A quién notifica?',
  tipo: 'seleccion_multiple',
  texto: null,
  opciones_elegidas: [0, 2],
  opciones_elegidas_texto: ['Regulador', 'Clientes'],
}

function abrir(respuestas: RespuestaRegistrada[] | number) {
  const fetchFalso = vi.fn(async (url: string) => {
    if (url.endsWith('/respuestas')) {
      return typeof respuestas === 'number'
        ? respuesta(respuestas, { detail: 'Sesión no encontrada' })
        : respuesta(200, respuestas)
    }
    return respuesta(200, {
      id: ID,
      nombre: 'Simulacro Q4',
      estado: 'finalizada',
    })
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/sesiones/:id/respuestas" element={<RespuestasSesionPage />} />
    </Routes>,
    { sesion: sesionDePrueba(MODERADOR), ruta: `/sesiones/${ID}/respuestas` },
  )
  return fetchFalso
}

describe('Registro de respuestas de la sesión', () => {
  it('muestra cada respuesta con participante, rol, inject, tarea y tiempo', async () => {
    abrir([BASE, OPCIONES])

    expect(await screen.findByText('Aíslo el file server')).toBeInTheDocument()
    expect(screen.getByText(/Simulacro Q4 · 2 respuestas/)).toBeInTheDocument()
    expect(screen.getByText(/Solo lectura/)).toBeInTheDocument()
    const fila = screen.getByText('Ana López').closest('tr') as HTMLElement
    expect(within(fila).getByText('CISO')).toBeInTheDocument()
    expect(within(fila).getByText('1. Detección')).toBeInTheDocument()
    expect(within(fila).getByText('1:05 / 5:00')).toBeInTheDocument()
    expect(screen.getByText('Regulador')).toBeInTheDocument()
    expect(screen.getByText('Clientes')).toBeInTheDocument()
    // Sin acciones para modificar ni borrar.
    expect(screen.queryByRole('button', { name: /eliminar|editar|borrar/i })).toBeNull()
  })

  it('filtra por rol', async () => {
    abrir([BASE, OPCIONES])
    await screen.findByText('Aíslo el file server')

    await userEvent.selectOptions(screen.getByLabelText('Rol'), 'legal')
    expect(screen.queryByText('Aíslo el file server')).toBeNull()
    expect(screen.getByText('Carlos Ramírez')).toBeInTheDocument()
  })

  it('sin respuestas todavía, lo explica', async () => {
    abrir([])
    expect(
      await screen.findByText('Todavía no hay respuestas registradas en esta sesión.'),
    ).toBeInTheDocument()
  })

  it('sesión ajena o inexistente', async () => {
    abrir(404)
    expect(await screen.findByText(/Sesión no encontrada/)).toBeInTheDocument()
  })
})
