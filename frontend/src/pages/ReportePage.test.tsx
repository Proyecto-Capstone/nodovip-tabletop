import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { Reporte, SesionConReporte } from '../api/reportes'
import { ANALISTA, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { ReportePage } from './ReportePage'
import { ReportesPage } from './ReportesPage'

const ID = 'eeeeeeee-0000-0000-0000-000000000001'

const REPORTE: Reporte = {
  sesion_id: ID,
  nombre: 'Simulacro Q4',
  cliente: 'Banco Andino',
  escenario: 'Ransomware en sucursal',
  moderador: 'Mónica Moderadora',
  iniciada_en: '2026-11-02T14:00:00Z',
  finalizada_en: '2026-11-02T14:45:00Z',
  duracion_segundos: 2700,
  participantes: 2,
  injects_lanzados: 1,
  total_injects: 4,
  puntaje_total: 8,
  maximo_total: 20,
  porcentaje_total: 40,
  por_participante: [
    {
      nombre: 'Ana López',
      detalle: 'CISO',
      puntaje: 8,
      maximo: 10,
      porcentaje: 80,
      respondidas: 1,
      sin_responder: 0,
    },
    {
      nombre: 'Luis Paz',
      detalle: 'Legal',
      puntaje: 0,
      maximo: 10,
      porcentaje: 0,
      respondidas: 0,
      sin_responder: 1,
    },
  ],
  por_rol: [
    {
      nombre: 'CISO',
      detalle: '1 participante',
      puntaje: 8,
      maximo: 10,
      porcentaje: 80,
      respondidas: 1,
      sin_responder: 0,
    },
    {
      nombre: 'Legal',
      detalle: '1 participante',
      puntaje: 0,
      maximo: 10,
      porcentaje: 0,
      respondidas: 0,
      sin_responder: 1,
    },
  ],
  brechas: [
    {
      participante: 'Luis Paz',
      rol_codigo: 'legal',
      rol_nombre: 'Legal',
      tarea: 'Notificación regulatoria dentro de 72 horas',
      inject_orden: 1,
      tipo: 'sin_respuesta',
      tipo_etiqueta: 'Sin respuesta',
      severidad: 'alta',
      porcentaje: 0,
      detalle: ['Notificar al regulador'],
      recurrente_en: 2,
    },
  ],
  superadas: [],
  respuestas: [
    {
      recibida_en: '2026-11-02T14:03:05Z',
      participante: 'Ana López',
      rol_nombre: 'CISO',
      inject_orden: 1,
      tarea: '¿Aísla los servidores?',
      contenido: 'Aíslo el file server',
      puntaje: 8,
      puntaje_maximo: 10,
      ajustada: true,
    },
  ],
  recomendaciones: [
    {
      prioridad: 'alta',
      rol_nombre: 'Legal',
      texto: 'Brecha recurrente (también en 2 de 3 sesiones anteriores). Designar un responsable.',
      recurrente: true,
    },
  ],
  sesiones_anteriores: 3,
  pdf: {
    estado: 'generado',
    solicitado_en: '2026-11-02T14:45:01Z',
    generado_en: '2026-11-02T14:45:03Z',
    error: null,
  },
}

function abrirReporte(datos: Reporte | number, alRegenerar?: () => Response) {
  const fetchFalso = vi.fn(async (url: string) => {
    if (url.endsWith('/regenerar') && alRegenerar) return alRegenerar()
    return typeof datos === 'number'
      ? respuesta(datos, { detail: 'Reporte no disponible' })
      : respuesta(200, datos)
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/reportes/:id" element={<ReportePage />} />
    </Routes>,
    { sesion: sesionDePrueba(ANALISTA), ruta: `/reportes/${ID}` },
  )
  return fetchFalso
}

describe('Reporte de brechas', () => {
  it('muestra resumen, puntajes por rol, brechas, trazabilidad y recomendaciones', async () => {
    abrirReporte(REPORTE)
    expect(await screen.findByText('Reporte de cierre: Simulacro Q4')).toBeInTheDocument()
    expect(screen.getByText(/Cliente: Banco Andino/)).toBeInTheDocument()
    expect(screen.getByText(/Duración: 00:45:00/)).toBeInTheDocument()
    expect(screen.getByText('40 %')).toBeInTheDocument()
    expect(screen.getByText(/1 brechas se repiten/)).toBeInTheDocument()

    const indice = screen.getByRole('navigation', { name: 'Contenido del reporte' })
    expect(within(indice).getAllByRole('link')).toHaveLength(5)

    const brechas = screen.getByRole('region', { name: 'Brechas detectadas por rol' })
    const fila = within(brechas)
      .getByText('Notificación regulatoria dentro de 72 horas')
      .closest('tr') as HTMLElement
    expect(within(fila).getByText('Sin respuesta')).toBeInTheDocument()
    expect(within(fila).getByText('Alta')).toBeInTheDocument()
    expect(within(fila).getByText('Recurrente (2)')).toBeInTheDocument()

    const traza = screen.getByRole('region', { name: 'Trazabilidad de respuestas' })
    expect(within(traza).getByText('Aíslo el file server')).toBeInTheDocument()
    expect(within(traza).getByText('ajustado')).toBeInTheDocument()

    const recs = screen.getByRole('region', { name: 'Recomendaciones principales' })
    expect(within(recs).getByText(/Brecha recurrente/)).toBeInTheDocument()
    expect(screen.getByText('PDF listo')).toBeInTheDocument()
  })

  it('el botón Exportar PDF descarga desde la API', async () => {
    abrirReporte(REPORTE)
    const exportar = await screen.findByRole('link', { name: /Exportar PDF/ })
    expect(exportar).toHaveAttribute('href', `/api/reportes/${ID}/pdf`)
    expect(exportar).toHaveAttribute('download')
  })

  it('regenera el PDF y recarga el reporte', async () => {
    const fetchFalso = abrirReporte(REPORTE, () => respuesta(200, REPORTE.pdf))
    await userEvent.click(await screen.findByRole('button', { name: 'Regenerar PDF' }))
    await waitFor(() =>
      expect(
        fetchFalso.mock.calls.filter(([u]) => String(u).endsWith(`/reportes/${ID}`)),
      ).toHaveLength(2),
    )
  })

  it('muestra el error si el PDF no se pudo generar', async () => {
    abrirReporte(REPORTE, () =>
      respuesta(503, { detail: 'No se pudo generar el PDF: Pango no disponible' }),
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Regenerar PDF' }))
    expect(await screen.findByText(/Pango no disponible/)).toBeInTheDocument()
  })

  it('sesión no finalizada o ajena', async () => {
    abrirReporte(404)
    expect(await screen.findByText(/Reporte no disponible/)).toBeInTheDocument()
  })
})

describe('Lista de reportes', () => {
  it('muestra cada sesión finalizada con el estado de su PDF', async () => {
    const lista: SesionConReporte[] = [
      {
        id: ID,
        nombre: 'Simulacro Q4',
        cliente: 'Banco Andino',
        finalizada_en: '2026-11-02T14:45:00Z',
        participantes: 2,
        reporte: REPORTE.pdf,
      },
      {
        id: 'otro',
        nombre: 'Prueba',
        cliente: null,
        finalizada_en: null,
        participantes: 1,
        reporte: { estado: 'fallido', solicitado_en: '', generado_en: null, error: 'Pango' },
      },
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => respuesta(200, lista)),
    )
    renderConSesion(<ReportesPage />, { sesion: sesionDePrueba(ANALISTA), ruta: '/reportes' })
    expect(await screen.findByText('Simulacro Q4')).toBeInTheDocument()
    expect(screen.getByText('PDF listo')).toBeInTheDocument()
    expect(screen.getByText('Falló el PDF')).toBeInTheDocument()
    expect(screen.getByText('Sin cliente')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Ver reporte' })[0]).toHaveAttribute(
      'href',
      `/reportes/${ID}`,
    )
  })
})
