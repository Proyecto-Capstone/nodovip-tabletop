import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { PuntajesSesion, RespuestaRegistrada } from '../api/respuestas'
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
  puntaje: 8.5,
  puntaje_automatico: 8.5,
  puntaje_maximo: 10,
  completitud: 1,
  precision: 0.75,
  tiempo: 0.9,
  aciertos: ['Aislar el servidor'],
  faltantes: [],
  errores: [],
  ajustes: [],
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

const PUNTAJES: PuntajesSesion = {
  participantes: [
    {
      usuario_id: 'u1',
      nombre: 'Ana López',
      rol_codigo: 'ciso',
      rol_nombre: 'CISO',
      puntaje: 8.5,
      maximo: 20,
      porcentaje: 42.5,
      respondidas: 1,
      sin_responder: 1,
    },
  ],
  roles: [
    {
      rol_codigo: 'ciso',
      rol_nombre: 'CISO',
      participantes: 1,
      puntaje: 8.5,
      maximo: 20,
      porcentaje: 42.5,
      respondidas: 1,
      sin_responder: 1,
    },
  ],
}

function abrir(
  respuestas: RespuestaRegistrada[] | number,
  alAjustar?: (cuerpo: { puntaje: number; motivo: string }) => Response,
) {
  const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/ajustes') && alAjustar) return alAjustar(JSON.parse(String(init?.body)))
    if (url.endsWith('/puntajes')) return respuesta(200, PUNTAJES)
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
    const fila = screen.getByText('¿Aísla los servidores?').closest('tr') as HTMLElement
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

  it('muestra el puntaje de cada respuesta y el acumulado', async () => {
    abrir([BASE])
    const fila = (await screen.findByText('Aíslo el file server')).closest('tr') as HTMLElement
    expect(within(fila).getByText('8,5 / 10')).toBeInTheDocument()
    expect(within(fila).getByText('✓ Aislar el servidor')).toBeInTheDocument()
    expect(within(fila).getByText('Precisión: 75 %')).toBeInTheDocument()

    const acumulado = screen.getByRole('region', { name: 'Puntaje acumulado' })
    expect(within(acumulado).getAllByText('8,5')).toHaveLength(2)
    expect(within(acumulado).getByText('1 de 2')).toBeInTheDocument()
  })

  it('ajusta el puntaje con motivo y recarga', async () => {
    let enviado: unknown
    const fetchFalso = abrir([BASE], (cuerpo) => {
      enviado = cuerpo
      return respuesta(201, { ...BASE, puntaje: 6 })
    })
    await screen.findByText('Aíslo el file server')

    await userEvent.click(screen.getByRole('button', { name: 'Ajustar' }))
    const puntaje = screen.getByLabelText('Nuevo puntaje')
    await userEvent.clear(puntaje)
    await userEvent.type(puntaje, '6')
    await userEvent.type(screen.getByLabelText('Motivo del ajuste'), 'Faltó justificar')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar ajuste' }))

    await waitFor(() => expect(screen.queryByLabelText('Nuevo puntaje')).toBeNull())
    expect(enviado).toEqual({ puntaje: 6, motivo: 'Faltó justificar' })
    // Recarga el registro y el acumulado.
    const pedidas = fetchFalso.mock.calls.map(([url]) => String(url))
    expect(pedidas.filter((u) => u.endsWith('/respuestas')).length).toBeGreaterThan(1)
    expect(pedidas.filter((u) => u.endsWith('/puntajes')).length).toBeGreaterThan(1)
  })

  it('muestra los errores del ajuste', async () => {
    abrir([BASE], () =>
      respuesta(422, { detail: { errores: ['El puntaje debe estar entre 0 y 10'] } }),
    )
    await screen.findByText('Aíslo el file server')
    await userEvent.click(screen.getByRole('button', { name: 'Ajustar' }))
    await userEvent.type(screen.getByLabelText('Motivo del ajuste'), 'Motivo largo')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar ajuste' }))
    expect(await screen.findByText('El puntaje debe estar entre 0 y 10')).toBeInTheDocument()
  })

  it('una respuesta ajustada muestra el automático y el historial', async () => {
    abrir([
      {
        ...BASE,
        puntaje: 6,
        ajustes: [
          {
            id: 'a1',
            puntaje_anterior: 8.5,
            puntaje_nuevo: 6,
            motivo: 'Faltó justificar',
            creado_en: '2026-11-02T14:10:00Z',
          },
        ],
      },
    ])
    const fila = (await screen.findByText('Aíslo el file server')).closest('tr') as HTMLElement
    expect(within(fila).getByText('6 / 10')).toBeInTheDocument()
    expect(within(fila).getByText('Ajustado')).toBeInTheDocument()
    expect(within(fila).getByText(/8,5 → 6\. «Faltó justificar»/)).toBeInTheDocument()
  })
})
