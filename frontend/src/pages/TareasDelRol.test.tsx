import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { VistaEnVivo } from '../api/enVivo'
import type { MiSesion, TareaParticipante } from '../api/misSesiones'
import { PARTICIPANTE, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { SesionEnVivoPage } from './SesionEnVivoPage'

const ID = 'cccccccc-0000-0000-0000-000000000001'

class SocketFalso {
  static ultimo: SocketFalso
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null
  constructor() {
    SocketFalso.ultimo = this
  }
  close() {}
  recibir(vista: Partial<VistaEnVivo>) {
    act(() =>
      this.onmessage?.({ data: JSON.stringify({ tipo: 'estado', vista: { ...VISTA, ...vista } }) }),
    )
  }
}

const VISTA: VistaEnVivo = {
  sesion_id: ID,
  nombre: 'Simulacro Q4',
  estado: 'en_curso',
  total_injects: 2,
  inject_actual: 1,
  inject: { orden: 1, titulo: 'Detección', descripcion: 'Archivos cifrados' },
  pausada: false,
  iniciada_en: '2026-11-02T14:00:00Z',
  inject_lanzado_en: '2026-11-02T14:01:00Z',
  segundos_transcurridos: 60,
  duracion_minutos: 60,
  version: 2,
  total_conectados: 2,
  conectados: null,
}

const MI_SESION = {
  id: ID,
  nombre: 'Simulacro Q4',
  estado: 'en_curso',
  rol_nombre: 'Director Ejecutivo',
} as MiSesion

const TEXTO: TareaParticipante = {
  id: 't1',
  inject_orden: 1,
  tipo: 'texto_libre',
  enunciado: '¿Autoriza el pago del rescate?',
  opciones: [],
  tiempo_limite_segundos: 300,
  segundos_restantes: 154,
  estado: 'pendiente',
  respuesta: null,
}

function abrir(tareas: TareaParticipante[], alResponder?: (url: string, cuerpo: unknown) => Response) {
  const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/respuesta') && alResponder) {
      return alResponder(url, JSON.parse(String(init?.body)))
    }
    if (url.endsWith('/tareas')) return respuesta(200, tareas)
    return respuesta(200, MI_SESION)
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/mis-sesiones/:id/en-vivo" element={<SesionEnVivoPage />} />
    </Routes>,
    { sesion: sesionDePrueba(PARTICIPANTE), ruta: `/mis-sesiones/${ID}/en-vivo` },
  )
  return fetchFalso
}

beforeEach(() => {
  vi.stubGlobal('WebSocket', SocketFalso)
})

describe('Tareas del rol en la sala', () => {
  it('muestra la pregunta con el tiempo restante y envía la respuesta una vez', async () => {
    const fetchFalso = abrir([TEXTO], (_url, cuerpo) =>
      respuesta(201, {
        ...TEXTO,
        estado: 'respondida',
        segundos_restantes: 0,
        respuesta: { texto: (cuerpo as { texto: string }).texto, opciones_elegidas: [], recibida_en: '' },
      }),
    )
    await screen.findByText('Rol: Director Ejecutivo')
    SocketFalso.ultimo.recibir({})

    expect(await screen.findByText('¿Autoriza el pago del rescate?')).toBeInTheDocument()
    expect(screen.getByText('Tu tarea — Director Ejecutivo')).toBeInTheDocument()
    expect(screen.getByLabelText('Tiempo restante: 154 segundos')).toHaveTextContent('02:34')
    const enviar = screen.getByRole('button', { name: 'Enviar respuesta →' })
    expect(enviar).toBeDisabled() // sin texto todavía

    await userEvent.type(screen.getByLabelText('Tu respuesta'), 'No autorizo el pago')
    await userEvent.click(enviar)

    expect(await screen.findByText(/Respuesta enviada/)).toBeInTheDocument()
    expect(screen.getByText('No autorizo el pago')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enviar respuesta →' })).toBeNull()
    const post = fetchFalso.mock.calls.find(([url]) => String(url).endsWith('/respuesta'))
    expect(post?.[0]).toBe(`/api/mis-sesiones/${ID}/tareas/t1/respuesta`)
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ texto: 'No autorizo el pago' })
  })

  it('selección múltiple: envía los índices elegidos', async () => {
    const opcion: TareaParticipante = {
      ...TEXTO,
      id: 't2',
      tipo: 'seleccion_multiple',
      enunciado: '¿Qué hace primero?',
      opciones: ['Aislar', 'Pagar', 'Avisar'],
    }
    let enviado: unknown
    abrir([opcion], (_url, cuerpo) => {
      enviado = cuerpo
      return respuesta(201, { ...opcion, estado: 'respondida', respuesta: { texto: null, opciones_elegidas: [0, 2], recibida_en: '' } })
    })
    await screen.findByText('Rol: Director Ejecutivo')
    SocketFalso.ultimo.recibir({})
    await screen.findByText('¿Qué hace primero?')

    await userEvent.click(screen.getByLabelText('Aislar'))
    await userEvent.click(screen.getByLabelText('Avisar'))
    await userEvent.click(screen.getByRole('button', { name: 'Enviar respuesta →' }))

    expect(await screen.findByText(/Respuesta enviada/)).toBeInTheDocument()
    expect(enviado).toEqual({ opciones: [0, 2] })
    expect(screen.getByLabelText('Aislar')).toBeChecked()
    expect(screen.getByLabelText('Pagar')).not.toBeChecked()
  })

  it('una tarea vencida queda bloqueada', async () => {
    abrir([{ ...TEXTO, estado: 'vencida', segundos_restantes: 0 }])
    await screen.findByText('Rol: Director Ejecutivo')
    SocketFalso.ultimo.recibir({})

    expect(await screen.findByText('Se agotó el tiempo para esta tarea.')).toBeInTheDocument()
    expect(screen.getByLabelText('Tu respuesta')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Enviar respuesta →' })).toBeNull()
  })

  it('en pausa no se puede enviar y el reloj se detiene', async () => {
    abrir([TEXTO])
    await screen.findByText('Rol: Director Ejecutivo')
    SocketFalso.ultimo.recibir({ pausada: true, version: 3 })

    const tarjeta = (await screen.findByText('¿Autoriza el pago del rescate?')).closest('form') as HTMLElement
    expect(within(tarjeta).getByLabelText('Tu respuesta')).toBeDisabled()
    expect(within(tarjeta).getByRole('button', { name: 'Enviar respuesta →' })).toBeDisabled()
  })

  it('si el servidor dice que ya respondió, muestra el aviso', async () => {
    abrir([TEXTO], () => respuesta(409, { detail: 'Ya respondiste esta tarea: no se puede cambiar' }))
    await screen.findByText('Rol: Director Ejecutivo')
    SocketFalso.ultimo.recibir({})
    await userEvent.type(await screen.findByLabelText('Tu respuesta'), 'Otra')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar respuesta →' }))

    expect(await screen.findByText(/Ya respondiste esta tarea/)).toBeInTheDocument()
  })

  it('sin tareas todavía, lo explica', async () => {
    abrir([])
    await screen.findByText('Rol: Director Ejecutivo')
    SocketFalso.ultimo.recibir({ inject_actual: 0, inject: null })
    expect(await screen.findByText(/Todavía no hay tareas para tu rol/)).toBeInTheDocument()
  })
})
