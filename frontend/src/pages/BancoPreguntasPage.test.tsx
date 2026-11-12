import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TareaBanco } from '../api/escenarios'
import {
  ADMINISTRADOR,
  MODERADOR,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { BancoPreguntasPage } from './BancoPreguntasPage'

function pregunta(id: string, cambios: Partial<TareaBanco>): TareaBanco {
  return {
    id,
    enunciado: `Pregunta ${id}`,
    rol_codigo: 'ti',
    dificultad: 'medio',
    criterios: ['Aislar la red', 'Avisar al CISO'],
    puntaje_maximo: 10,
    tiempo_limite_segundos: 300,
    respuesta_esperada: null,
    tipo: 'texto_libre',
    opciones: [],
    inject_orden: 1,
    escenario_id: 'e1',
    escenario_nombre: 'Ransomware en archivos',
    tipo_codigo: 'ransomware',
    ...cambios,
  }
}

const BANCO: TareaBanco[] = [
  pregunta('1', { enunciado: '¿Qué aísla primero?', respuesta_esperada: 'Los servidores' }),
  pregunta('2', {
    enunciado: '¿Cómo clasifica el evento?',
    rol_codigo: 'ciso',
    tipo: 'seleccion_multiple',
    criterios: [],
    opciones: [
      { texto: 'Falso positivo', correcta: false },
      { texto: 'Incidente grave', correcta: true },
    ],
    inject_orden: 2,
  }),
  pregunta('3', {
    enunciado: '¿A quién avisa?',
    escenario_id: 'e2',
    escenario_nombre: 'Phishing financiero',
    tipo_codigo: 'phishing',
  }),
]

function simularApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.includes('tipos-escenario')) {
        return respuesta(200, [
          { codigo: 'ransomware', nombre: 'Ransomware' },
          { codigo: 'phishing', nombre: 'Phishing' },
        ])
      }
      if (url.includes('roles-ejercicio')) {
        return respuesta(200, [
          { codigo: 'ti', nombre: 'Responsable de TI' },
          { codigo: 'ciso', nombre: 'CISO' },
        ])
      }
      if (url.includes('/banco-preguntas')) return respuesta(200, BANCO)
      return respuesta(200, [])
    }),
  )
}

afterEach(() => vi.unstubAllGlobals())

const panel = () => screen.getByRole('complementary', { name: 'Evaluación y rúbrica' })

describe('BancoPreguntasPage', () => {
  it('agrupa por escenario y muestra la rúbrica de la primera pregunta de la lista', async () => {
    simularApi()
    renderConSesion(<BancoPreguntasPage />, { sesion: sesionDePrueba(ADMINISTRADOR) })

    const grupos = await screen.findAllByRole('region', { name: /Phishing|Ransomware/ })
    expect(grupos.map((g) => g.getAttribute('aria-label'))).toEqual([
      'Phishing financiero',
      'Ransomware en archivos',
    ])
    // Elegida por defecto: la primera que se ve (grupo Phishing).
    expect(within(panel()).getAllByText('¿A quién avisa?')).not.toHaveLength(0)

    await userEvent.click(screen.getByRole('button', { name: /¿Qué aísla primero\?/ }))
    expect(within(panel()).getByText('Aislar la red')).toBeInTheDocument()
    expect(within(panel()).getByText('Los servidores')).toBeInTheDocument()
    expect(within(panel()).getByRole('link', { name: /Editar en el escenario/ })).toHaveAttribute(
      'href',
      '/escenarios/e1/editar',
    )
  })

  it('al elegir una pregunta de selección marca la opción correcta', async () => {
    simularApi()
    renderConSesion(<BancoPreguntasPage />, { sesion: sesionDePrueba(ADMINISTRADOR) })

    await userEvent.click(
      await screen.findByRole('button', { name: /¿Cómo clasifica el evento\?/ }),
    )

    expect(screen.getByRole('button', { name: /¿Cómo clasifica el evento\?/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    const correcta = within(panel()).getByText('(correcta)').closest('li')!
    expect(correcta).toHaveTextContent('Incidente grave')
  })

  it('busca por texto y agrupa por momento del ejercicio', async () => {
    simularApi()
    renderConSesion(<BancoPreguntasPage />, { sesion: sesionDePrueba(MODERADOR) })

    await userEvent.selectOptions(await screen.findByLabelText('Agrupar por'), 'inject')
    expect(screen.getByRole('region', { name: 'Inject 1' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Inject 2' })).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Buscar'), 'avisa')
    expect(screen.getByRole('button', { name: /¿A quién avisa\?/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /¿Qué aísla primero\?/ })).not.toBeInTheDocument()
    // El moderador no edita escenarios: solo puede verlos.
    expect(within(panel()).queryByRole('link', { name: /Editar/ })).not.toBeInTheDocument()
  })
})
