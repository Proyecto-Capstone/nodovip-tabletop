import { act, screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { DetalleMonitoreo } from '../api/monitoreo'
import { ADMINISTRADOR, PARTICIPANTE, renderConSesion, sesionDePrueba } from '../test/utilidades'
import { MonitoreoSesionPage } from './MonitoreoSesionPage'

const ID = 'cccccccc-0000-0000-0000-000000000001'
const ANA = 'bbbbbbbb-0000-0000-0000-00000000000a'
const CARLOS = 'bbbbbbbb-0000-0000-0000-00000000000b'

/** WebSocket simulado: las pruebas deciden cuándo abre, qué llega y cómo cierra. */
class SocketFalso {
  static todos: SocketFalso[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null
  url: string
  constructor(url: string) {
    this.url = url
    SocketFalso.todos.push(this)
  }
  close() {}
  abrir() {
    act(() => this.onopen?.())
  }
  recibir(datos: DetalleMonitoreo) {
    act(() => this.onmessage?.({ data: JSON.stringify({ tipo: 'monitoreo', datos }) }))
  }
  caer(code = 1006) {
    act(() => this.onclose?.({ code }))
  }
}

const ultimo = () => SocketFalso.todos[SocketFalso.todos.length - 1]

const BASE: DetalleMonitoreo = {
  sesion: {
    id: ID,
    nombre: 'Simulacro Q4',
    moderador_nombre: 'Mónica Moderadora',
    escenario_nombre: 'Ransomware',
    pausada: false,
    invitados: 2,
    conectados: 1,
    inject_actual: 1,
    total_injects: 3,
    respuestas_recibidas: 1,
    respuestas_esperadas: 2,
    porcentaje_avance: 50,
    segundos_transcurridos: 65,
    iniciada_en: '2026-01-10T09:00:00Z',
    duracion_minutos: 60,
    excede_duracion: false,
  },
  participantes: [
    {
      usuario_id: ANA,
      nombre: 'Ana López',
      rol_codigo: 'ciso',
      rol_nombre: 'CISO',
      puntaje: 8,
      maximo: 10,
      porcentaje: 80,
      respondidas: 1,
      sin_responder: 0,
    },
    {
      usuario_id: CARLOS,
      nombre: 'Carlos Ramírez',
      rol_codigo: 'legal',
      rol_nombre: 'Legal',
      puntaje: 0,
      maximo: 10,
      porcentaje: 0,
      respondidas: 0,
      sin_responder: 1,
    },
  ],
  roles: [
    {
      rol_codigo: 'ciso',
      rol_nombre: 'CISO',
      participantes: 1,
      puntaje: 8,
      maximo: 10,
      porcentaje: 80,
      respondidas: 1,
      sin_responder: 0,
    },
    {
      rol_codigo: 'legal',
      rol_nombre: 'Legal',
      participantes: 1,
      puntaje: 0,
      maximo: 10,
      porcentaje: 0,
      respondidas: 0,
      sin_responder: 1,
    },
  ],
  conectados_ids: [ANA],
}

function rutas() {
  return (
    <Routes>
      <Route path="/monitoreo/:id" element={<MonitoreoSesionPage />} />
    </Routes>
  )
}

beforeEach(() => {
  SocketFalso.todos = []
  vi.stubGlobal('WebSocket', SocketFalso)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('MonitoreoSesionPage', () => {
  it('sin el permiso sesiones:monitorear no se muestra la página', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(PARTICIPANTE), ruta: `/monitoreo/${ID}` })
    expect(screen.getByText(/Sin acceso/)).toBeInTheDocument()
  })

  it('muestra el aviso de modo lectura y el avance, sin comandos ni texto de respuestas', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: `/monitoreo/${ID}` })
    ultimo().abrir()
    ultimo().recibir(BASE)

    expect(await screen.findByText('Simulacro Q4')).toBeInTheDocument()
    expect(
      screen.getByText('Modo lectura — no puedes controlar esta sesión.'),
    ).toBeInTheDocument()

    // Avance por participante y por rol, igual que el panel del moderador.
    const progreso = screen.getByRole('region', { name: 'Progreso por participante — Inject 1' })
    expect(within(progreso).getByText('Ana López')).toBeInTheDocument()
    expect(within(progreso).getByText('Carlos Ramírez')).toBeInTheDocument()
    expect(within(progreso).getByText('Respondido')).toBeInTheDocument()

    const avanceRol = screen.getByRole('region', { name: 'Avance por rol' })
    expect(within(avanceRol).getByText('CISO')).toBeInTheDocument()
    expect(within(avanceRol).getByText('Legal')).toBeInTheDocument()

    // Nunca texto de respuestas, opciones elegidas ni criterios (PB-10).
    expect(screen.queryByText('Respuestas recientes')).not.toBeInTheDocument()
    expect(screen.queryByText(/Aíslo los servidores/)).not.toBeInTheDocument()

    // Ningún botón de comando ni de ajuste de puntaje: solo lectura.
    for (const nombre of [
      /Iniciar sesión/,
      /Lanzar inject/,
      /Pausar/,
      /Reanudar/,
      /Cerrar sesión/,
      /Ajustar/,
    ]) {
      expect(screen.queryByRole('button', { name: nombre })).not.toBeInTheDocument()
    }
  })

  it('marca como conectado solo a quien está en conectados_ids', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: `/monitoreo/${ID}` })
    ultimo().abrir()
    ultimo().recibir(BASE)

    const progreso = await screen.findByRole('region', { name: 'Progreso por participante — Inject 1' })
    const filaAna = within(progreso).getByText('Ana López').closest('li') as HTMLElement
    const filaCarlos = within(progreso).getByText('Carlos Ramírez').closest('li') as HTMLElement
    expect(within(filaAna).getByText('CISO · Conectado')).toBeInTheDocument()
    expect(within(filaCarlos).getByText('Legal · Sin conexión')).toBeInTheDocument()
  })

  it('un cierre definitivo muestra el error', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: `/monitoreo/${ID}` })
    ultimo().abrir()
    ultimo().caer(4404)

    expect(await screen.findByText('Esta sesión ya no está en curso.')).toBeInTheDocument()
  })
})
