import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Acceso } from '../api/accesos'
import { ADMINISTRADOR, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { AccesosPage } from './AccesosPage'

const ACCESOS: Acceso[] = [
  {
    id: 3,
    fecha_hora: '2026-11-11T21:00:00Z',
    correo: 'ana@demo.nodovip.test',
    usuario_id: 'u1',
    ip: '172.18.0.1',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0) Chrome/157.0 Safari/537.36',
    resultado: 'exitoso',
  },
  {
    id: 2,
    fecha_hora: '2026-11-11T20:00:00Z',
    correo: 'nadie@demo.nodovip.test',
    usuario_id: null,
    ip: '200.25.1.4',
    user_agent: 'Python-urllib/3.14',
    resultado: 'credenciales_invalidas',
  },
  {
    id: 1,
    fecha_hora: '2026-11-11T19:00:00Z',
    correo: 'ana@demo.nodovip.test',
    usuario_id: 'u1',
    ip: '172.18.0.1',
    user_agent: null,
    resultado: 'bloqueado',
  },
]

afterEach(() => vi.unstubAllGlobals())

function abrir() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => respuesta(200, ACCESOS)),
  )
  renderConSesion(<AccesosPage />, { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/accesos' })
}

const inspector = () => screen.getByRole('complementary', { name: /Intento de acceso/ })

describe('AccesosPage', () => {
  it('resume los eventos y abre el primero en el inspector', async () => {
    abrir()
    const resumen = await screen.findByRole('region', { name: 'Resumen de accesos' })
    expect(within(resumen).getByText('Eventos registrados').nextSibling).toHaveTextContent('3')
    expect(within(resumen).getByText('Intentos fallidos').nextSibling).toHaveTextContent('1')
    expect(within(resumen).getByText('Bloqueos').nextSibling).toHaveTextContent('1')

    expect(within(inspector()).getByText('Intento de acceso #3')).toBeInTheDocument()
    expect(within(inspector()).getByText('Riesgo estimado: Bajo')).toBeInTheDocument()
    expect(within(inspector()).getByText('Chrome 157')).toBeInTheDocument()
  })

  it('filtra por grupo y muestra en el inspector el intento elegido', async () => {
    abrir()
    await userEvent.click(await screen.findByRole('button', { name: /^Fallidos/ }))
    const registro = screen.getByRole('region', { name: /Registro de eventos/ })
    expect(within(registro).getAllByRole('button')).toHaveLength(1)

    expect(within(inspector()).getByText('Intento de acceso #2')).toBeInTheDocument()
    expect(within(inspector()).getByText('Riesgo estimado: Medio')).toBeInTheDocument()
    expect(within(inspector()).getByText(/red externa/)).toBeInTheDocument()
    expect(within(inspector()).getByText(/no corresponde a ninguna cuenta/)).toBeInTheDocument()
    expect(within(inspector()).getByText(/script o de una herramienta/)).toBeInTheDocument()

    await userEvent.click(within(inspector()).getByRole('tab', { name: 'Registro JSON' }))
    expect(within(inspector()).getByRole('tabpanel')).toHaveTextContent(
      '"resultado": "credenciales_invalidas"',
    )
  })
})
