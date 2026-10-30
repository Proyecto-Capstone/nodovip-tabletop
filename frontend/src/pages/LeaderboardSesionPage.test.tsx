import { act, screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Leaderboard } from '../api/leaderboard'
import { OBSERVADOR, renderConSesion, sesionDePrueba } from '../test/utilidades'
import { LeaderboardSesionPage } from './LeaderboardSesionPage'

const ID = 'cccccccc-0000-0000-0000-000000000001'

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
  recibir(datos: Leaderboard) {
    act(() => this.onmessage?.({ data: JSON.stringify({ tipo: 'leaderboard', datos }) }))
  }
  caer(code = 1006) {
    act(() => this.onclose?.({ code }))
  }
}

const ultimo = () => SocketFalso.todos[SocketFalso.todos.length - 1]

const BASE: Leaderboard = {
  sesion: {
    id: ID,
    nombre: 'Simulacro Q4',
    estado: 'en_curso',
    total_injects: 3,
    inject_actual: 1,
    iniciada_en: '2026-01-10T09:00:00Z',
    finalizada_en: null,
  },
  actualizado_en: '2026-01-10T09:05:00Z',
  participantes: [
    {
      posicion: 1,
      usuario_id: 'p1',
      nombre: 'Ana López',
      rol_codigo: 'ti',
      rol_nombre: 'TI',
      puntaje: 10,
      maximo: 10,
      porcentaje: 100,
      respondidas: 1,
      sin_responder: 0,
    },
    {
      posicion: 2,
      usuario_id: 'p2',
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
      posicion: 1,
      rol_codigo: 'ti',
      rol_nombre: 'TI',
      participantes: 1,
      puntaje: 10,
      maximo: 10,
      porcentaje: 100,
      respondidas: 1,
      sin_responder: 0,
    },
    {
      posicion: 2,
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
}

function rutas() {
  return (
    <Routes>
      <Route path="/leaderboard/:id" element={<LeaderboardSesionPage />} />
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

describe('LeaderboardSesionPage', () => {
  it('muestra el ranking al llegar el primer mensaje', async () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(OBSERVADOR),
      ruta: `/leaderboard/${ID}`,
    })
    expect(screen.getByText('Cargando…')).toBeInTheDocument()
    ultimo().abrir()
    ultimo().recibir(BASE)

    expect(await screen.findByText('Simulacro Q4')).toBeInTheDocument()

    const podio = screen.getByRole('group', { name: 'Podio' })
    expect(within(podio).getByText('Ana López')).toBeInTheDocument()
    expect(within(podio).getByText('🥇')).toBeInTheDocument()
    expect(within(podio).getByText('10 pts')).toBeInTheDocument()

    const roles = screen.getByRole('region', { name: 'Ranking por rol organizacional' })
    expect(within(roles).getByText('TI')).toBeInTheDocument()
    expect(within(roles).getByText('10 / 10 pts')).toBeInTheDocument()

    const completo = screen.getByRole('region', { name: 'Ranking completo' })
    expect(within(completo).getByText('Carlos Ramírez')).toBeInTheDocument()

    expect(screen.getByText('● EN VIVO')).toBeInTheDocument()
  })

  it('sin participantes muestra un aviso y sin podio', async () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(OBSERVADOR),
      ruta: `/leaderboard/${ID}`,
    })
    ultimo().abrir()
    ultimo().recibir({ ...BASE, participantes: [] })

    expect(
      await screen.findByText('Todavía no hay participantes en esta sesión.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Podio' })).not.toBeInTheDocument()
  })

  it('un cierre definitivo muestra el error', async () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(OBSERVADOR),
      ruta: `/leaderboard/${ID}`,
    })
    ultimo().abrir()
    ultimo().caer(4404)

    expect(
      await screen.findByText(/No encontramos esta sesión entre las visibles/),
    ).toBeInTheDocument()
  })

  it('actualiza el ranking al llegar un nuevo mensaje del WebSocket, sin recargar', async () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(OBSERVADOR),
      ruta: `/leaderboard/${ID}`,
    })
    ultimo().abrir()
    ultimo().recibir(BASE)
    await screen.findByText('Simulacro Q4')

    const actualizado: Leaderboard = {
      ...BASE,
      participantes: [
        { ...BASE.participantes[1], posicion: 1, puntaje: 10, porcentaje: 100 },
        { ...BASE.participantes[0], posicion: 2, puntaje: 0, porcentaje: 0 },
      ],
    }
    ultimo().recibir(actualizado)

    const podio = await screen.findByRole('group', { name: 'Podio' })
    expect(within(podio).getByText('Carlos Ramírez')).toBeInTheDocument()
    expect(within(podio).queryByText('Ana López')).not.toBeInTheDocument()

    const completo = screen.getByRole('region', { name: 'Ranking completo' })
    const filas = within(completo).getAllByRole('listitem')
    expect(within(filas[0]).getByText('Carlos Ramírez')).toBeInTheDocument()
    expect(within(filas[1]).getByText('Ana López')).toBeInTheDocument()
  })

  it('muestra "Resultado final" cuando la sesión termina', async () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(OBSERVADOR),
      ruta: `/leaderboard/${ID}`,
    })
    ultimo().abrir()
    ultimo().recibir({ ...BASE, sesion: { ...BASE.sesion, estado: 'finalizada' } })

    expect(await screen.findByText('Resultado final')).toBeInTheDocument()
    expect(screen.queryByText('● EN VIVO')).not.toBeInTheDocument()
  })

  it('un empate en 0 puntos no muestra medalla ni fondo de podio', async () => {
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(OBSERVADOR),
      ruta: `/leaderboard/${ID}`,
    })
    ultimo().abrir()
    ultimo().recibir({
      ...BASE,
      participantes: [
        { ...BASE.participantes[0], nombre: 'Diana Flores', posicion: 1, puntaje: 10, porcentaje: 100 },
        { ...BASE.participantes[1], usuario_id: 'p2', nombre: 'Ana López', posicion: 2, puntaje: 0, porcentaje: 0 },
        { ...BASE.participantes[1], usuario_id: 'p3', nombre: 'Pedro Morales', posicion: 2, puntaje: 0, porcentaje: 0 },
        { ...BASE.participantes[1], usuario_id: 'p4', nombre: 'Pedro Suárez', posicion: 2, puntaje: 0, porcentaje: 0 },
      ],
    })

    // El podio solo tiene a la ganadora: ningún empatado en 0 entra, aunque
    // su posición (por el empate) sea 2 y por lo tanto <= 3.
    const podio = await screen.findByRole('group', { name: 'Podio' })
    expect(within(podio).getByText('Diana Flores')).toBeInTheDocument()
    for (const nombre of ['Ana López', 'Pedro Morales', 'Pedro Suárez']) {
      expect(within(podio).queryByText(nombre)).not.toBeInTheDocument()
    }

    const completo = screen.getByRole('region', { name: 'Ranking completo' })
    for (const nombre of ['Ana López', 'Pedro Morales', 'Pedro Suárez']) {
      const fila = within(completo)
        .getAllByRole('listitem')
        .find((f) => within(f).queryByText(nombre)) as HTMLElement
      expect(fila.className).not.toContain('leaderboard-podio')
    }
  })
})
