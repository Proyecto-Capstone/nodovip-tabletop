import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Debrief } from '../api/debrief'
import type { Reporte } from '../api/reportes'
import type { Sesion } from '../api/auth'
import { ANALISTA, MODERADOR, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { DebriefPage } from './DebriefPage'

const ID = 'ffffffff-0000-0000-0000-000000000001'

const VACIO: Debrief = {
  sesion_id: ID,
  sesion_nombre: 'Simulacro Q4',
  cliente: 'Banco Andino',
  finalizada_en: '2026-11-02T15:00:00Z',
  estado: 'sin_iniciar',
  fortalezas: [],
  mejoras: [],
  acciones: [],
  actualizado_en: null,
  completado_en: null,
  puede_editar: true,
  roles: [
    { codigo: 'ti', nombre: 'Responsable de TI' },
    { codigo: 'legal', nombre: 'Legal' },
  ],
}

const REPORTE = {
  sesion_id: ID,
  porcentaje_total: 40,
  brechas: [{}, {}],
  recomendaciones: [
    {
      prioridad: 'alta',
      rol_nombre: 'Responsable de TI',
      texto: 'Probar la restauración de respaldos',
      recurrente: false,
    },
  ],
} as unknown as Reporte

function abrir(
  sesion: Sesion,
  debrief: Debrief,
  alCompletar: () => Response = () => respuesta(200, { ...debrief, estado: 'completado' }),
) {
  const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes('/reportes/')) return respuesta(200, REPORTE)
    if (url.endsWith('/completar')) return alCompletar()
    if (init?.method === 'PUT') {
      return respuesta(200, {
        ...debrief,
        estado: 'borrador',
        actualizado_en: '2026-11-10T15:00:00Z',
      })
    }
    return respuesta(200, debrief)
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/sesiones/:id/debrief" element={<DebriefPage />} />
    </Routes>,
    { sesion: sesionDePrueba(sesion), ruta: `/sesiones/${ID}/debrief` },
  )
  return fetchFalso
}

const cuerpoDelPut = (fetchFalso: ReturnType<typeof vi.fn>) => {
  const llamada = fetchFalso.mock.calls.find(([, init]) => init?.method === 'PUT')
  return JSON.parse(String(llamada?.[1]?.body))
}

describe('Debrief (PC-45)', () => {
  it('registra fortalezas, mejoras y una acción y guarda el borrador', async () => {
    const fetchFalso = abrir(MODERADOR, VACIO)
    expect(await screen.findByText('Debrief: Simulacro Q4')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Fortaleza 1'), 'Escalaron rápido')
    await userEvent.type(screen.getByLabelText('Aspecto a mejorar 1'), 'Respaldos sin probar')
    await userEvent.click(screen.getByRole('button', { name: '+ Agregar acción' }))
    await userEvent.type(screen.getByLabelText('Qué se hará'), 'Simulacro trimestral')
    await userEvent.selectOptions(screen.getByLabelText('Responsable'), 'legal')
    expect(screen.getByText('Cambios sin guardar')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))
    expect(await screen.findByText('Borrador guardado.')).toBeInTheDocument()
    expect(cuerpoDelPut(fetchFalso)).toEqual({
      fortalezas: ['Escalaron rápido'],
      mejoras: ['Respaldos sin probar'],
      acciones: [
        {
          descripcion: 'Simulacro trimestral',
          prioridad: 'media',
          rol_codigo: 'legal',
          plazo: null,
        },
      ],
    })
  })

  it('suma una recomendación del reporte al plan con su responsable y prioridad', async () => {
    abrir(MODERADOR, VACIO)
    const hallazgos = await screen.findByRole('complementary', {
      name: 'Hallazgos del ejercicio',
    })
    await userEvent.click(within(hallazgos).getByRole('button', { name: '+ Agregar al plan' }))
    expect(screen.getByLabelText('Qué se hará')).toHaveValue('Probar la restauración de respaldos')
    expect(screen.getByLabelText('Responsable')).toHaveValue('ti')
    expect(screen.getByLabelText('Prioridad')).toHaveValue('alta')
  })

  it('al completar muestra lo que falta', async () => {
    abrir(MODERADOR, VACIO, () =>
      respuesta(422, {
        detail: { errores: ['Agrega al menos una acción al plan'] },
      }),
    )
    await screen.findByText('Debrief: Simulacro Q4')
    await userEvent.click(screen.getByRole('button', { name: 'Completar debrief' }))
    expect(await screen.findByText(/Agrega al menos una acción al plan/)).toBeInTheDocument()
  })

  it('completado se ve en solo lectura y se puede reabrir', async () => {
    abrir(MODERADOR, {
      ...VACIO,
      estado: 'completado',
      completado_en: '2026-11-10T15:00:00Z',
      fortalezas: ['Escalaron rápido'],
      mejoras: ['Respaldos sin probar'],
      acciones: [
        {
          descripcion: 'Simulacro trimestral',
          prioridad: 'alta',
          rol_codigo: null,
          plazo: '2026-12-15',
          responsable: 'Toda la organización',
        },
      ],
    })
    expect(await screen.findByText('Simulacro trimestral')).toBeInTheDocument()
    expect(screen.getByText('Toda la organización')).toBeInTheDocument()
    expect(screen.getByText('15 dic 2026')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Guardar borrador' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Reabrir para editar' })).toBeInTheDocument()
  })

  it('el analista no edita y ve un aviso si todavía no hay debrief', async () => {
    abrir(ANALISTA, { ...VACIO, puede_editar: false })
    expect(await screen.findByText(/todavía no registró el debrief/)).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Completar debrief' })).toBeNull(),
    )
  })
})
