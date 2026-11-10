import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { EscenarioDetalle } from '../api/escenarios'
import { ADMINISTRADOR, renderConSesion, respuesta, sesionDePrueba } from '../test/utilidades'
import { EscenarioFormPage } from './EscenarioFormPage'

const ID = 'aaaaaaaa-0000-0000-0000-000000000046'

const ESCENARIO: EscenarioDetalle = {
  id: ID,
  nombre: 'Ransomware de prueba',
  tipo_codigo: 'ransomware',
  nivel: 'alto',
  estado: 'borrador',
  roles: ['ti'],
  total_injects: 3,
  total_tareas: 1,
  descripcion: 'Cifrado de servidores con nota de rescate en cada carpeta.',
  es_base: true,
  pendientes_para_publicar: [],
  injects: [1, 2, 3].map((n) => ({
    id: `inject-${n}`,
    orden: n,
    titulo: `Inject ${n} de prueba`,
    descripcion: 'Ocurre un evento nuevo',
    minuto_sugerido: null,
    evidencia: null,
  })),
  tareas: [
    {
      id: 'tarea-1',
      enunciado: '¿Cómo contiene la propagación?',
      rol_codigo: 'ti',
      dificultad: 'medio',
      criterios: ['Aísla la red'],
      puntaje_maximo: 10,
      tiempo_limite_segundos: 300,
      respuesta_esperada: null,
      tipo: 'texto_libre',
      opciones: [],
      inject_orden: null,
    },
  ],
}

function abrir() {
  const fetchFalso = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/catalogos/tipos-escenario')) {
      return respuesta(200, [
        {
          codigo: 'ransomware',
          nombre: 'Ransomware',
          descripcion: '',
          nivel_complejidad: 'alto',
          roles_sugeridos: [],
        },
      ])
    }
    if (url.endsWith('/catalogos/roles-ejercicio')) {
      return respuesta(200, [{ codigo: 'ti', nombre: 'Responsable de TI' }])
    }
    if (init?.method === 'PUT') return respuesta(200, ESCENARIO)
    return respuesta(200, ESCENARIO)
  })
  vi.stubGlobal('fetch', fetchFalso)
  renderConSesion(
    <Routes>
      <Route path="/escenarios/:id/editar" element={<EscenarioFormPage />} />
      <Route path="/escenarios/:id" element={<p>Detalle</p>} />
    </Routes>,
    { sesion: sesionDePrueba(ADMINISTRADOR), ruta: `/escenarios/${ID}/editar` },
  )
  return fetchFalso
}

describe('Formulario del escenario: preguntas (PC-46)', () => {
  it('convierte la pregunta en selección múltiple y la asigna a un inject', async () => {
    const fetchFalso = abrir()
    const tarea = await screen.findByRole('group', { name: 'Tarea 1' })

    await userEvent.selectOptions(within(tarea).getByLabelText('Se pregunta en'), 'inject-2')
    await userEvent.selectOptions(
      within(tarea).getByLabelText('Tipo de respuesta'),
      'seleccion_multiple',
    )
    // Los criterios se cambian por el editor de opciones.
    expect(within(tarea).queryByLabelText(/Criterios de evaluación/)).toBeNull()
    await userEvent.type(within(tarea).getByLabelText('Texto de la opción 1'), 'Aislar la red')
    await userEvent.type(within(tarea).getByLabelText('Texto de la opción 2'), 'Pagar el rescate')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() =>
      expect(fetchFalso.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(true),
    )
    const [, init] = fetchFalso.mock.calls.find(([, i]) => i?.method === 'PUT')!
    const [enviada] = JSON.parse(String(init!.body)).tareas
    expect(enviada).toMatchObject({
      tipo: 'seleccion_multiple',
      inject_orden: 2,
      opciones: [
        { texto: 'Aislar la red', correcta: true },
        { texto: 'Pagar el rescate', correcta: false },
      ],
    })
  })
})
