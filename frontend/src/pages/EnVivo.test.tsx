import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ResumenParticipante } from '../api/debrief'
import type { InjectEnVivo, VistaEnVivo } from '../api/enVivo'
import type { MiSesion } from '../api/misSesiones'
import type { SesionDetalle } from '../api/sesiones'
import {
  MODERADOR,
  PARTICIPANTE,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { ConducirSesionPage } from './ConducirSesionPage'
import { SesionEnVivoPage } from './SesionEnVivoPage'

const ID = 'cccccccc-0000-0000-0000-000000000001'
const ANA = 'bbbbbbbb-0000-0000-0000-00000000000a'

/** WebSocket simulado: las pruebas deciden cuándo abre, qué llega y cómo cierra. */
class SocketFalso {
  static todos: SocketFalso[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: ((e: { code: number }) => void) | null = null
  cerrado = false
  url: string
  constructor(url: string) {
    this.url = url
    SocketFalso.todos.push(this)
  }
  close() {
    this.cerrado = true
  }
  abrir() {
    act(() => this.onopen?.())
  }
  recibir(vista: Partial<VistaEnVivo>) {
    act(() => this.onmessage?.({ data: JSON.stringify({ tipo: 'estado', vista: { ...VISTA, ...vista } }) }))
  }
  /** Aviso de respuesta nueva: solo lo recibe el moderador (PB-11). */
  avisarRespuesta() {
    act(() => this.onmessage?.({ data: JSON.stringify({ tipo: 'respuesta' }) }))
  }
  /** Aviso de ajuste de puntaje (PB-10): recarga el panel igual que una respuesta. */
  avisarAjuste() {
    act(() => this.onmessage?.({ data: JSON.stringify({ tipo: 'ajuste' }) }))
  }
  caer(code = 1006) {
    act(() => this.onclose?.({ code }))
  }
}

const ultimo = () => SocketFalso.todos[SocketFalso.todos.length - 1]

const VISTA: VistaEnVivo = {
  sesion_id: ID,
  nombre: 'Simulacro Q4',
  estado: 'programada',
  total_injects: 3,
  inject_actual: 0,
  inject: null,
  lanzados: [],
  pausada: false,
  iniciada_en: null,
  inject_lanzado_en: null,
  segundos_transcurridos: 0,
  duracion_minutos: 60,
  version: 0,
  total_conectados: 1,
  conectados: null,
}

const RESUMEN: ResumenParticipante = {
  sesion_id: ID,
  nombre: 'Simulacro Q4',
  finalizada_en: '2026-11-02T15:00:00Z',
  rol_nombre: 'CISO',
  puntaje: 7.5,
  maximo: 10,
  porcentaje: 75,
  posicion: 1,
  total_participantes: 3,
  tareas: [
    {
      inject_orden: 1,
      inject_titulo: 'Detección inicial',
      enunciado: '¿A quién escala el incidente?',
      tipo: 'texto_libre',
      puntaje_maximo: 10,
      respondida: true,
      respuesta: 'A la dirección',
      puntaje: 7.5,
      aciertos: ['Escalar a la dirección'],
      faltantes: ['Mencionar al regulador'],
      errores: [],
      opciones_correctas: [],
      ajuste_motivo: 'Buena priorización',
    },
  ],
  lecciones: null,
}

const INJECT_1: InjectEnVivo = {
  orden: 1,
  titulo: 'Detección inicial',
  descripcion: 'TI detecta archivos cifrados',
  evidencia: {
    tipo: 'alerta',
    origen: 'EDR corporativo',
    asunto: 'Cifrado masivo en FS-01',
    contenido: '18.412 archivos renombrados a .lock',
    nivel: 'critica',
  },
  lanzado_segundo: 5,
}
const INJECT_2: InjectEnVivo = {
  orden: 2,
  titulo: 'Nota de rescate',
  descripcion: 'Piden 40 BTC en 72 horas',
  evidencia: {
    tipo: 'correo',
    origen: 'soporte@extorsion.example',
    asunto: 'Sus datos — 24 horas',
    contenido: 'Pague o publicamos todo.',
    nivel: null,
  },
  lanzado_segundo: 900,
}

const MI_SESION: MiSesion = {
  id: ID,
  nombre: 'Simulacro Q4',
  estado: 'programada',
  fecha_programada: '2026-11-02T14:00:00Z',
  duracion_minutos: 60,
  escenario_nombre: 'Ransomware',
  escenario_descripcion: 'Cifrado',
  moderador_nombre: 'Mónica',
  rol_codigo: 'ciso',
  rol_nombre: 'CISO',
  total_participantes: 1,
  invitacion: 'aceptada',
  invitacion_aceptada_en: null,
}

beforeEach(() => {
  SocketFalso.todos = []
  vi.stubGlobal('WebSocket', SocketFalso)
})

afterEach(() => {
  vi.useRealTimers()
})

function abrirParticipante() {
  // Las tareas del rol se piden aparte (PB-08): aquí no hay ninguna. Al
  // finalizar se pide el resumen del participante (PC-45).
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const ruta = String(url)
      if (ruta.includes('/tareas')) return respuesta(200, [])
      if (ruta.includes('/resumen')) return respuesta(200, RESUMEN)
      return respuesta(200, MI_SESION)
    }),
  )
  renderConSesion(
    <Routes>
      <Route path="/mis-sesiones/:id/en-vivo" element={<SesionEnVivoPage />} />
    </Routes>,
    { sesion: sesionDePrueba(PARTICIPANTE), ruta: `/mis-sesiones/${ID}/en-vivo` },
  )
}

describe('Sala del participante', () => {
  it('sigue la sesión: espera, inject, pausa y fin', async () => {
    abrirParticipante()
    expect(await screen.findByText('Rol: CISO')).toBeInTheDocument()
    expect(ultimo().url).toBe(`ws://localhost:3000/api/ws/sesiones/${ID}`)

    ultimo().abrir()
    ultimo().recibir({})
    expect(screen.getByText(/todavía no empieza/)).toBeInTheDocument()

    ultimo().recibir({ estado: 'en_curso', inject_actual: 1, inject: INJECT_1, version: 2 })
    expect(screen.getByText('TI detecta archivos cifrados')).toBeInTheDocument()
    expect(screen.getByText('Inject 1 de 3')).toBeInTheDocument()
    expect(screen.getByText('EN VIVO')).toBeInTheDocument()

    ultimo().recibir({ estado: 'en_curso', inject_actual: 1, inject: INJECT_1, pausada: true, version: 3 })
    expect(screen.getByText(/pausó la sesión/)).toBeInTheDocument()

    ultimo().recibir({ estado: 'finalizada', inject_actual: 1, version: 4 })
    // PC-45: al terminar ve su resultado y la retroalimentación de cada tarea.
    expect(await screen.findByText('Tu resultado como CISO')).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('Comentario del moderador:')).toBeInTheDocument()
    expect(screen.getByText('Mencionar al regulador')).toBeInTheDocument()
    expect(screen.getByText(/compartirá aquí las lecciones/)).toBeInTheDocument()
  })

  it('avisa del inject nuevo, muestra su evidencia y la línea de tiempo (PC-44)', async () => {
    abrirParticipante()
    await screen.findByText('Rol: CISO')
    ultimo().abrir()
    // La primera vista (al entrar) no avisa aunque ya haya un inject.
    ultimo().recibir({
      estado: 'en_curso',
      inject_actual: 1,
      inject: INJECT_1,
      lanzados: [INJECT_1],
      version: 2,
    })
    expect(screen.queryByText('Nuevo inject 1')).toBeNull()
    expect(
      screen.getByRole('article', { name: /Alerta de seguridad.*Cifrado masivo/ }),
    ).toBeInTheDocument()
    expect(screen.getByText('Crítica')).toBeInTheDocument()

    ultimo().recibir({
      estado: 'en_curso',
      inject_actual: 2,
      inject: INJECT_2,
      lanzados: [INJECT_1, INJECT_2],
      version: 3,
    })
    expect(screen.getByText('Nuevo inject 2')).toBeInTheDocument()
    expect(
      screen.getByRole('article', { name: /Correo electrónico: Sus datos/ }),
    ).toBeInTheDocument()
    // El inject anterior queda en la línea de tiempo, con el momento en que se lanzó.
    const linea = screen.getByRole('region', { name: 'Línea de tiempo del incidente' })
    expect(within(linea).getByText('Inject 1 · Detección inicial')).toBeInTheDocument()
    expect(within(linea).getByText('00:00:05')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Cerrar aviso' }))
    expect(screen.queryByText('Nuevo inject 2')).toBeNull()
  })

  it('el sonido del aviso se puede silenciar y se recuerda', async () => {
    abrirParticipante()
    await screen.findByText('Rol: CISO')
    const boton = screen.getByRole('button', { name: /Sonido activado/ })
    expect(boton).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(boton)
    expect(screen.getByRole('button', { name: /Silenciado/ })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(localStorage.getItem('nodovip_sonido_injects')).toBe('no')
    localStorage.removeItem('nodovip_sonido_injects')
  })

  it('si se cae la conexión, reconecta y recupera el estado actual', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    abrirParticipante()
    await screen.findByText('Rol: CISO')
    ultimo().abrir()
    ultimo().recibir({ estado: 'en_curso', inject_actual: 1, inject: INJECT_1, version: 2 })

    ultimo().caer()
    expect(screen.getByText(/Reconectando/)).toBeInTheDocument()
    expect(SocketFalso.todos).toHaveLength(1)

    act(() => vi.advanceTimersByTime(600))
    expect(SocketFalso.todos).toHaveLength(2)
    ultimo().abrir()
    // Mientras no estaba, el moderador lanzó el inject 2.
    ultimo().recibir({ estado: 'en_curso', inject_actual: 2, inject: INJECT_2, version: 3 })

    expect(screen.queryByText(/Reconectando/)).toBeNull()
    expect(screen.getByText('Piden 40 BTC en 72 horas')).toBeInTheDocument()
  })

  it('un cierre por falta de invitación no reintenta', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    abrirParticipante()
    await screen.findByText('Rol: CISO')
    ultimo().caer(4404)

    expect(screen.getByText(/No encontramos esta sesión/)).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(10_000))
    expect(SocketFalso.todos).toHaveLength(1)
  })

  it('cierra el socket al salir de la página y reconecta al volver con "atrás"', async () => {
    abrirParticipante()
    await screen.findByText('Rol: CISO')
    ultimo().abrir()

    act(() => {
      window.dispatchEvent(new Event('pagehide'))
    })
    expect(SocketFalso.todos[0].cerrado).toBe(true)

    const volver = new Event('pageshow') as PageTransitionEvent
    Object.defineProperty(volver, 'persisted', { value: true })
    act(() => {
      window.dispatchEvent(volver)
    })
    expect(SocketFalso.todos).toHaveLength(2)
  })

  it('ignora mensajes viejos que llegan tarde', async () => {
    abrirParticipante()
    await screen.findByText('Rol: CISO')
    ultimo().recibir({ estado: 'en_curso', inject_actual: 2, inject: INJECT_2, version: 5 })
    ultimo().recibir({ estado: 'en_curso', inject_actual: 1, inject: INJECT_1, version: 4 })
    expect(screen.getByText('Piden 40 BTC en 72 horas')).toBeInTheDocument()
  })
})

describe('Panel del moderador', () => {
  const PUNTAJES = (respondidas: number) => ({
    participantes: [
      {
        usuario_id: ANA,
        nombre: 'Ana López',
        rol_codigo: 'ciso',
        rol_nombre: 'CISO',
        puntaje: respondidas * 8,
        maximo: 10,
        porcentaje: respondidas * 80,
        respondidas,
        sin_responder: 1 - respondidas,
      },
    ],
    roles: [
      {
        rol_codigo: 'ciso',
        rol_nombre: 'CISO',
        participantes: 1,
        puntaje: respondidas * 8,
        maximo: 10,
        porcentaje: respondidas * 80,
        respondidas,
        sin_responder: 1 - respondidas,
      },
    ],
  })
  const RESPUESTA_ANA = {
    id: 'r1',
    recibida_en: '2026-11-02T14:03:05Z',
    participante_nombre: 'Ana López',
    rol_nombre: 'CISO',
    inject_orden: 1,
    puntaje: 8,
    puntaje_maximo: 10,
    texto: 'Aíslo los servidores y activo el plan de respuesta',
    opciones_elegidas_texto: [],
  }

  function abrirModerador(opciones: { respuestaIniciar?: () => Response } = {}) {
    // Cuántas respuestas devuelve el servidor (cambia cuando "llega" una).
    const servidor = { respondidas: 0 }
    const detalle = {
      id: ID,
      nombre: 'Simulacro Q4',
      estado: 'programada',
      injects: [
        { id: 'i1', orden: 1, titulo: 'Detección', minuto_sugerido: 0 },
        { id: 'i2', orden: 2, titulo: 'Extorsión', minuto_sugerido: 15 },
        { id: 'i3', orden: 3, titulo: 'Filtración', minuto_sugerido: null },
      ],
      participantes: [{ usuario_id: ANA, rol_codigo: 'ciso', invitacion: 'aceptada' }],
    } as unknown as SesionDetalle
    const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
      if (
        opciones.respuestaIniciar &&
        url === `/api/sesiones/${ID}/en-vivo/iniciar` &&
        init?.method === 'POST'
      ) {
        return opciones.respuestaIniciar()
      }
      if (url === `/api/sesiones/${ID}`) return respuesta(200, detalle)
      if (url === '/api/catalogos/roles-ejercicio') return respuesta(200, [{ codigo: 'ciso', nombre: 'CISO' }])
      if (url === '/api/sesiones/participantes-disponibles') {
        return respuesta(200, [{ id: ANA, nombre: 'Ana López', correo: 'ana@example.com' }])
      }
      if (url.endsWith('/puntajes')) return respuesta(200, PUNTAJES(servidor.respondidas))
      if (url.endsWith('/respuestas')) {
        return respuesta(200, servidor.respondidas ? [RESPUESTA_ANA] : [])
      }
      return respuesta(200, VISTA)
    })
    vi.stubGlobal('fetch', fetchFalso)
    renderConSesion(
      <Routes>
        <Route path="/sesiones/:id/conducir" element={<ConducirSesionPage />} />
      </Routes>,
      { sesion: sesionDePrueba(MODERADOR), ruta: `/sesiones/${ID}/conducir` },
    )
    return { fetchFalso, servidor }
  }

  const llamadas = (f: ReturnType<typeof vi.fn>) =>
    f.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST').map(([url]) => url)

  it('inicia la sesión y lanza injects con los comandos REST', async () => {
    const { fetchFalso } = abrirModerador()
    expect(await screen.findByText('Panel del moderador: Simulacro Q4')).toBeInTheDocument()
    ultimo().abrir()
    ultimo().recibir({ conectados: [ANA], total_conectados: 1 })

    expect(screen.getByText('CISO · Conectado')).toBeInTheDocument()
    expect(screen.getByText('1/1')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
    expect(llamadas(fetchFalso)).toEqual([`/api/sesiones/${ID}/en-vivo/iniciar`])

    ultimo().recibir({ estado: 'en_curso', version: 1, conectados: [ANA], segundos_transcurridos: 65 })
    expect(screen.getByText('00:01:05')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Lanzar inject 1' }))
    await userEvent.click(screen.getByRole('button', { name: 'Pausar' }))
    expect(llamadas(fetchFalso)).toEqual([
      `/api/sesiones/${ID}/en-vivo/iniciar`,
      `/api/sesiones/${ID}/en-vivo/lanzar-inject`,
      `/api/sesiones/${ID}/en-vivo/pausar`,
    ])
  })

  it('en pausa no deja lanzar injects y ofrece reanudar', async () => {
    abrirModerador()
    await screen.findByText('Panel del moderador: Simulacro Q4')
    ultimo().recibir({ estado: 'en_curso', pausada: true, version: 2, conectados: [] })

    expect(screen.getByRole('button', { name: 'Lanzar inject 1' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reanudar' })).toBeEnabled()
    expect(screen.getByText('En pausa')).toBeInTheDocument()
    expect(screen.getByText('CISO · Sin conexión')).toBeInTheDocument()
  })

  it('muestra el avance y lo actualiza cuando llega una respuesta, sin recargar', async () => {
    const { fetchFalso, servidor } = abrirModerador()
    await screen.findByText('Panel del moderador: Simulacro Q4')
    ultimo().recibir({ estado: 'en_curso', inject_actual: 1, version: 3, conectados: [ANA] })

    const avance = await screen.findByRole('region', { name: 'Avance por rol' })
    expect(await within(avance).findByText('0 de 1 respuestas · 1 pendientes')).toBeInTheDocument()
    expect(screen.getByText('Todavía no llegan respuestas.')).toBeInTheDocument()
    const progreso = screen.getByRole('region', { name: 'Progreso por participante — Inject 1' })
    expect(within(progreso).getByText('Sin respuesta')).toBeInTheDocument()
    expect(within(progreso).getByText('0%')).toBeInTheDocument()
    const injects = screen.getByRole('region', { name: 'Injects' })
    expect(within(injects).getByText('En curso')).toBeInTheDocument()
    expect(within(injects).getAllByText('Pendiente')).toHaveLength(2)

    // Un participante responde: el servidor avisa por WebSocket y el panel recarga.
    servidor.respondidas = 1
    const antes = fetchFalso.mock.calls.length
    ultimo().avisarRespuesta()

    expect(await within(avance).findByText('1 de 1 respuestas · 0 pendientes')).toBeInTheDocument()
    expect(fetchFalso.mock.calls.length).toBeGreaterThan(antes)
    expect(within(progreso).getByText('Respondido')).toBeInTheDocument()
    expect(within(progreso).getByText('100%')).toBeInTheDocument()
    const recientes = screen.getByRole('region', { name: 'Respuestas recientes' })
    expect(within(recientes).getByText('Ana López — CISO')).toBeInTheDocument()
    expect(
      within(recientes).getByText('Aíslo los servidores y activo el plan de respuesta'),
    ).toBeInTheDocument()
    expect(within(recientes).getByText('Inject 1 · 8 / 10 pts')).toBeInTheDocument()
    expect(screen.getByText('1/1', { selector: '.metrica strong:not(.metrica-verde)' })).toBeInTheDocument()
  })

  it('si el servidor rechaza por el límite de sesiones activas, muestra el mensaje tal cual', async () => {
    const mensaje =
      'Se alcanzó el máximo de 10 sesiones activas. Espera a que termine una o pide al administrador que amplíe el límite. 2 de las sesiones activas ya superan su duración programada.'
    abrirModerador({
      respuestaIniciar: () => respuesta(422, { detail: { errores: [mensaje] } }),
    })
    await screen.findByText('Panel del moderador: Simulacro Q4')
    ultimo().abrir()
    ultimo().recibir({ conectados: [ANA], total_conectados: 1 })

    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(mensaje)
  })

  it('también recarga el panel cuando llega un aviso de ajuste', async () => {
    const { fetchFalso, servidor } = abrirModerador()
    await screen.findByText('Panel del moderador: Simulacro Q4')
    ultimo().recibir({ estado: 'en_curso', inject_actual: 1, version: 3, conectados: [ANA] })
    const avance = await screen.findByRole('region', { name: 'Avance por rol' })
    await within(avance).findByText('0 de 1 respuestas · 1 pendientes')

    servidor.respondidas = 1
    const antes = fetchFalso.mock.calls.length
    ultimo().avisarAjuste()

    expect(await within(avance).findByText('1 de 1 respuestas · 0 pendientes')).toBeInTheDocument()
    expect(fetchFalso.mock.calls.length).toBeGreaterThan(antes)
  })
})
