import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { EscenarioDetalle, RolEjercicio, TipoEscenario } from '../api/escenarios'
import { ADMINISTRADOR, PARTICIPANTE, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { EscenarioDetallePage } from './EscenarioDetallePage'

const ID = '12121212-0000-0000-0000-000000000001'

const TIPOS: TipoEscenario[] = [
  { codigo: 'ransomware', nombre: 'Ransomware', descripcion: '', nivel_complejidad: 'medio', roles_sugeridos: [] },
]

const ROLES: RolEjercicio[] = [
  { codigo: 'ti', nombre: 'Responsable de TI' },
  { codigo: 'legal', nombre: 'Legal' },
]

function escenarioBase(): EscenarioDetalle {
  return {
    id: ID,
    nombre: 'Ransomware Sector Financiero',
    tipo_codigo: 'ransomware',
    nivel: 'medio',
    estado: 'borrador',
    roles: ['ti', 'legal'],
    total_injects: 1,
    total_tareas: 1,
    descripcion: 'Un ataque de ransomware cifra los servidores.',
    es_base: false,
    injects: [
      {
        id: 'i1',
        orden: 1,
        titulo: 'Cifrado masivo',
        descripcion: 'Archivos cifrados',
        minuto_sugerido: 0,
        evidencia: null,
      },
    ],
    tareas: [
      {
        id: 't1',
        enunciado: '¿Qué medidas se toman?',
        rol_codigo: 'ti',
        dificultad: 'medio',
        criterios: [],
        puntaje_maximo: 10,
        tiempo_limite_segundos: 300,
        respuesta_esperada: null,
        tipo: 'seleccion_multiple',
        opciones: [
          { texto: 'Aislar el servidor', correcta: true },
          { texto: 'Pagar el rescate', correcta: false },
        ],
        inject_orden: 1,
      },
    ],
    pendientes_para_publicar: [],
  }
}

function abrir(escenario = escenarioBase(), usuario = ADMINISTRADOR) {
  let actual = escenario
  const fetchFalso = vi.fn(async (url: string) => {
    if (url === `/api/escenarios/${ID}/archivar`) {
      actual = { ...actual, estado: 'archivado' }
      return respuesta(200, actual)
    }
    if (url === '/api/catalogos/tipos-escenario') return respuesta(200, TIPOS)
    if (url === '/api/catalogos/roles-ejercicio') return respuesta(200, ROLES)
    if (url === `/api/escenarios/${ID}`) return respuesta(200, actual)
    return respuesta(404, { detail: 'No encontrado' })
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/escenarios/:id" element={<EscenarioDetallePage />} />
    </Routes>,
    { sesion: sesionDePrueba(usuario), ruta: `/escenarios/${ID}` },
  )
  return fetchFalso
}

describe('EscenarioDetallePage', () => {
  it('sin permiso de lectura muestra el aviso', () => {
    abrir(escenarioBase(), PARTICIPANTE)
    expect(screen.getByRole('alert')).toHaveTextContent('Sin acceso')
  })

  it('marca la opción correcta sin revelarla en texto visible más que para lectores de pantalla', async () => {
    abrir()
    await screen.findByText('Ransomware Sector Financiero')

    await userEvent.click(screen.getByText('Opciones (2)'))
    const correcta = screen.getByText('Aislar el servidor').closest('li') as HTMLElement
    expect(correcta.className).toContain('opcion-correcta')
    expect(within(correcta).getByText('Correcta:')).toBeInTheDocument()

    const incorrecta = screen.getByText('Pagar el rescate').closest('li') as HTMLElement
    expect(incorrecta.className).not.toContain('opcion-correcta')
  })

  it('archivar pide confirmación antes de llamar al backend', async () => {
    const fetchFalso = abrir()
    await screen.findByText('Ransomware Sector Financiero')

    await userEvent.click(screen.getByRole('button', { name: 'Archivar' }))
    const dialogo = await screen.findByRole('alertdialog')
    expect(dialogo).toHaveTextContent('¿Archivar el escenario?')

    await userEvent.click(within(dialogo).getByRole('button', { name: 'Archivar' }))

    expect(await screen.findByText('Archivado')).toBeInTheDocument()
    expect(
      fetchFalso.mock.calls.some(([url]) => url === `/api/escenarios/${ID}/archivar`),
    ).toBe(true)
  })

  it('cancelar la confirmación de archivar no llama al backend', async () => {
    const fetchFalso = abrir()
    await screen.findByText('Ransomware Sector Financiero')

    await userEvent.click(screen.getByRole('button', { name: 'Archivar' }))
    await screen.findByRole('alertdialog')
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(
      fetchFalso.mock.calls.some(([url]) => String(url).endsWith('/archivar')),
    ).toBe(false)
  })
})
