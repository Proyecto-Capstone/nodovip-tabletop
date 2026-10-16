import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { SesionDetalle } from '../api/sesiones'
import {
  MODERADOR,
  PARTICIPANTE,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { DisenadorPage } from './DisenadorPage'

const INJECT_1 = 'aaaaaaaa-0000-0000-0000-000000000001'
const INJECT_2 = 'aaaaaaaa-0000-0000-0000-000000000002'
const ANA = 'bbbbbbbb-0000-0000-0000-00000000000a'
const LUIS = 'bbbbbbbb-0000-0000-0000-00000000000b'

function sesionBase(): SesionDetalle {
  return {
    id: 'cccccccc-0000-0000-0000-000000000001',
    nombre: 'Ransomware Sector Financiero',
    escenario_id: 'dddddddd-0000-0000-0000-000000000001',
    estado: 'borrador',
    fecha_programada: null,
    duracion_minutos: null,
    roles: ['ti', 'legal'],
    total_participantes: 0,
    puntaje_maximo_total: 20,
    injects: [
      { id: INJECT_1, orden: 1, titulo: 'Cifrado masivo', descripcion: 'Archivos cifrados', minuto_sugerido: 0 },
      { id: INJECT_2, orden: 2, titulo: 'Nota de rescate', descripcion: 'Piden 500 000 USD', minuto_sugerido: 15 },
    ],
    tareas: [
      {
        id: 't1',
        inject_id: INJECT_1,
        rol_codigo: 'ti',
        tipo: 'texto_libre',
        enunciado: '¿Cómo contiene la propagación?',
        opciones: [],
        criterios: ['Aísla la red'],
        dificultad: 'medio',
        puntaje_maximo: 10,
        tiempo_limite_segundos: 300,
        respuesta_esperada: null,
      },
      {
        id: 't2',
        inject_id: INJECT_2,
        rol_codigo: 'legal',
        tipo: 'texto_libre',
        enunciado: '¿Autoriza el pago del rescate?',
        opciones: [],
        criterios: ['Considera riesgos legales'],
        dificultad: 'alto',
        puntaje_maximo: 10,
        tiempo_limite_segundos: 300,
        respuesta_esperada: null,
      },
    ],
    participantes: [],
    pesos: { completitud: 40, precision: 40, tiempo: 20 },
    pendientes_para_programar: ['Debe tener fecha y hora programadas'],
  }
}

/** Simula el backend: GET fijos y PUT/POST que devuelven lo guardado. */
function simularApi(sesion = sesionBase()) {
  let actual = sesion
  const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
    const metodo = init?.method ?? 'GET'
    if (url === '/api/catalogos/roles-ejercicio') {
      return respuesta(200, [
        { codigo: 'legal', nombre: 'Legal' },
        { codigo: 'ti', nombre: 'Responsable de TI' },
        { codigo: 'ciso', nombre: 'CISO' },
      ])
    }
    if (url === '/api/sesiones/participantes-disponibles') {
      return respuesta(200, [
        { id: ANA, nombre: 'Ana López', correo: 'ana@example.com' },
        { id: LUIS, nombre: 'Luis Suárez', correo: 'luis@example.com' },
      ])
    }
    if (url.startsWith('/api/escenarios/')) {
      return respuesta(200, { nombre: 'Ransomware — Sector Financiero' })
    }
    if (url === `/api/sesiones/${actual.id}` && metodo === 'PUT') {
      const cuerpo = JSON.parse(String(init?.body))
      actual = {
        ...actual,
        ...cuerpo,
        injects: cuerpo.injects.map((i: object, n: number) => ({ ...i, orden: n + 1 })),
      }
      return respuesta(200, actual)
    }
    if (url === `/api/sesiones/${actual.id}/programar`) {
      actual = { ...actual, estado: 'programada' }
      return respuesta(200, actual)
    }
    if (url === `/api/sesiones/${actual.id}`) return respuesta(200, actual)
    return respuesta(404, { detail: 'No encontrado' })
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

function abrir(paso: number, usuario = MODERADOR) {
  renderConSesion(
    <Routes>
      <Route path="/sesiones/:id/disenar" element={<DisenadorPage />} />
    </Routes>,
    {
      sesion: sesionDePrueba(usuario),
      ruta: `/sesiones/${sesionBase().id}/disenar?paso=${paso}`,
    },
  )
}

const cuerposPut = (fetchFalso: ReturnType<typeof simularApi>) =>
  fetchFalso.mock.calls
    .filter(([, init]) => init?.method === 'PUT')
    .map(([, init]) => JSON.parse(String(init?.body)))

describe('DisenadorPage', () => {
  it('sin permiso de diseño muestra el aviso', () => {
    simularApi()
    abrir(2, PARTICIPANTE)
    expect(screen.getByRole('alert')).toHaveTextContent('Sin acceso')
  })

  it('paso 2: asigna participantes y al avanzar guarda el borrador', async () => {
    const fetchFalso = simularApi()
    abrir(2)

    expect(
      await screen.findByRole('heading', { name: 'Paso 2 — Configurar roles' }),
    ).toBeInTheDocument()
    expect(await screen.findByText(/Escenario: Ransomware — Sector Financiero/)).toBeInTheDocument()

    await userEvent.selectOptions(
      screen.getByLabelText('Participante para Responsable de TI'),
      ANA,
    )
    // Ana ya tiene rol: no se ofrece para Legal.
    const selectLegal = screen.getByLabelText('Participante para Legal')
    expect(within(selectLegal).queryByText(/Ana López/)).toBeNull()
    await userEvent.selectOptions(selectLegal, LUIS)

    await userEvent.click(screen.getByRole('button', { name: 'Paso siguiente →' }))

    expect(
      await screen.findByRole('heading', { name: 'Paso 3 — Asignar tareas e injects por rol' }),
    ).toBeInTheDocument()
    expect(cuerposPut(fetchFalso)[0].participantes).toEqual([
      { usuario_id: ANA, rol_codigo: 'ti' },
      { usuario_id: LUIS, rol_codigo: 'legal' },
    ])
  })

  it('paso 3: muestra las tareas por rol e inject y agrega una de selección múltiple', async () => {
    const fetchFalso = simularApi()
    abrir(3)

    const panel = await screen.findByRole('heading', {
      name: 'Responsable de TI — Tareas asignadas',
    })
    const seccion = panel.closest('section') as HTMLElement
    expect(within(seccion).getByText('Inject 1')).toBeInTheDocument()
    expect(within(seccion).getByText('¿Cómo contiene la propagación?')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Legal/ }))
    const legal = screen
      .getByRole('heading', { name: 'Legal — Tareas asignadas' })
      .closest('section') as HTMLElement
    expect(within(legal).getByText('Inject 2')).toBeInTheDocument()

    await userEvent.click(within(legal).getByRole('button', { name: '+ Agregar tarea al inject' }))
    await userEvent.type(
      within(legal).getByLabelText('Pregunta o tarea'),
      '¿Se emite un comunicado oficial?',
    )
    await userEvent.selectOptions(
      within(legal).getByLabelText('Tipo de respuesta'),
      'seleccion_multiple',
    )
    await userEvent.type(within(legal).getByLabelText('Texto de la opción 1'), 'Sí')
    await userEvent.type(within(legal).getByLabelText('Texto de la opción 2'), 'No')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))

    expect(await screen.findByText('Borrador guardado.')).toBeInTheDocument()
    const nueva = cuerposPut(fetchFalso)[0].tareas.at(-1)
    expect(nueva).toMatchObject({
      rol_codigo: 'legal',
      // El inject 1 es el primero en el que Legal todavía no tenía tarea.
      inject_id: INJECT_1,
      tipo: 'seleccion_multiple',
      opciones: [
        { texto: 'Sí', correcta: true },
        { texto: 'No', correcta: false },
      ],
    })
  })

  it('paso 4: el puntaje total se calcula solo y avisa si los pesos no suman 100', async () => {
    simularApi()
    abrir(4)

    expect(await screen.findByTestId('puntaje-total')).toHaveTextContent('20')
    const puntaje = screen.getByLabelText('Puntaje máximo: ¿Cómo contiene la propagación?')
    await userEvent.clear(puntaje)
    await userEvent.type(puntaje, '25')
    expect(screen.getByTestId('puntaje-total')).toHaveTextContent('35')

    const tiempo = screen.getByLabelText('Tiempo (%)')
    await userEvent.clear(tiempo)
    await userEvent.type(tiempo, '30')
    expect(screen.getByText(/Suma: 110 %/)).toHaveTextContent('debe ser 100 %')
  })

  it('paso 5: programa la sesión', async () => {
    const fetchFalso = simularApi()
    abrir(5)

    expect(await screen.findByText('Debe tener fecha y hora programadas')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Duración'), '90')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar y programar' }))

    expect(await screen.findByText(/Sesión programada/)).toBeInTheDocument()
    expect(cuerposPut(fetchFalso)[0].duracion_minutos).toBe(90)
    expect(
      fetchFalso.mock.calls.some(([url]) => String(url).endsWith('/programar')),
    ).toBe(true)
    expect(screen.getByText('Programada')).toBeInTheDocument()
  })

  it('muestra los errores del backend y no avanza', async () => {
    const fetchFalso = simularApi()
    abrir(4)
    await screen.findByTestId('puntaje-total')
    fetchFalso.mockImplementationOnce(async () =>
      respuesta(422, { detail: { errores: ['Los pesos de puntuación deben sumar 100'] } }),
    )
    const tiempo = screen.getByLabelText('Tiempo (%)')
    await userEvent.clear(tiempo)
    await userEvent.type(tiempo, '30')
    await userEvent.click(screen.getByRole('button', { name: 'Paso siguiente →' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('deben sumar 100')
    expect(
      screen.getByRole('heading', { name: 'Paso 4 — Criterios de puntuación' }),
    ).toBeInTheDocument()
  })
})

describe('formatoDuracion', () => {
  it('muestra horas y minutos', async () => {
    const { formatoDuracion } = await import('./disenador/comun')
    expect(formatoDuracion(45)).toBe('45 min')
    expect(formatoDuracion(90)).toBe('1 h 30 min')
    expect(formatoDuracion(120)).toBe('2 h')
  })
})
