import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EscenarioResumen, TipoEscenario } from '../api/escenarios'
import {
  ADMINISTRADOR,
  MODERADOR,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from '../test/utilidades'
import { BibliotecaPage } from './BibliotecaPage'

const TIPOS: TipoEscenario[] = ['ransomware', 'phishing', 'ddos', 'fuga'].map((codigo) => ({
  codigo,
  nombre: codigo.toUpperCase(),
  descripcion: '',
  nivel_complejidad: 'medio',
  roles_sugeridos: [],
}))

function escenario(
  id: string,
  estado: EscenarioResumen['estado'],
  tipo_codigo: string,
): EscenarioResumen {
  return {
    id,
    nombre: `Escenario ${id}`,
    tipo_codigo,
    nivel: 'alto',
    estado,
    roles: ['ti'],
    total_injects: 4,
    total_tareas: 8,
  }
}

const ACTIVOS = [
  escenario('a', 'publicado', 'ransomware'),
  escenario('b', 'publicado', 'phishing'),
  escenario('c', 'borrador', 'ddos'),
]

/** Simula la API: catálogos, la lista (con o sin filtro de estado) y crear sesión. */
function simularApi() {
  const fetchSimulado = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST' && url.endsWith('/sesiones')) {
      return respuesta(201, { id: 'sesion-1' })
    }
    if (url.includes('tipos-escenario')) return respuesta(200, TIPOS)
    if (url.includes('roles-ejercicio')) return respuesta(200, [{ codigo: 'ti', nombre: 'TI' }])
    if (url.includes('estado=archivado'))
      return respuesta(200, [escenario('z', 'archivado', 'fuga')])
    if (url.includes('/escenarios')) return respuesta(200, ACTIVOS)
    return respuesta(200, [])
  })
  vi.stubGlobal('fetch', fetchSimulado)
  return fetchSimulado
}

afterEach(() => vi.unstubAllGlobals())

function rutas() {
  return (
    <Routes>
      <Route path="/" element={<BibliotecaPage />} />
      <Route path="/sesiones/:id/disenar" element={<p>Diseñador</p>} />
    </Routes>
  )
}

describe('BibliotecaPage', () => {
  it('muestra los indicadores de toda la biblioteca al administrador', async () => {
    simularApi()
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })

    const resumen = await screen.findByRole('region', { name: 'Resumen de la biblioteca' })
    expect(await within(resumen).findByText('2 de 4')).toBeInTheDocument()
    expect(within(resumen).getByText('1 archivados aparte')).toBeInTheDocument()
    expect(within(resumen).getByText('50%')).toBeInTheDocument()
    expect(within(resumen).getByText('Publicados').nextSibling).toHaveTextContent('2')
    expect(within(resumen).getByText('En borrador').nextSibling).toHaveTextContent('1')
  })

  it('al administrador le ofrece ver y editar, no diseñar', async () => {
    simularApi()
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR) })

    const tarjeta = (await screen.findByText('Escenario a')).closest('article')!
    expect(within(tarjeta).getByRole('link', { name: 'Ver detalle' })).toHaveAttribute(
      'href',
      '/escenarios/a',
    )
    expect(within(tarjeta).getByRole('link', { name: 'Editar Escenario a' })).toHaveAttribute(
      'href',
      '/escenarios/a/editar',
    )
    expect(screen.queryByRole('button', { name: /Diseñar tabletop/ })).not.toBeInTheDocument()
  })

  it('el moderador diseña un tabletop desde la tarjeta', async () => {
    const fetchSimulado = simularApi()
    renderConSesion(rutas(), { sesion: sesionDePrueba(MODERADOR) })

    const tarjeta = (await screen.findByText('Escenario a')).closest('article')!
    expect(within(tarjeta).queryByRole('link', { name: /Editar/ })).not.toBeInTheDocument()
    await userEvent.click(within(tarjeta).getByRole('button', { name: /Diseñar tabletop/ }))

    expect(await screen.findByText('Diseñador')).toBeInTheDocument()
    const crear = fetchSimulado.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(crear?.[1]?.body))).toEqual({ escenario_id: 'a' })
  })
})
