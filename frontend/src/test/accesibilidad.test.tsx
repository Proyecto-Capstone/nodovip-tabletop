// PC-47: pruebas automáticas de accesibilidad (WCAG 2.1 A y AA) con axe-core.
// En jsdom no hay estilos reales: el contraste de color se auditó en Chrome
// con la misma herramienta (docs/seguridad.md). Aquí se vigilan etiquetas,
// roles, nombres accesibles, ARIA y estructura para que el CI detecte
// regresiones en cada PR.

import { render, screen } from '@testing-library/react'
import axe from 'axe-core'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { ResumenParticipante } from '../api/debrief'
import type { EscenarioResumen } from '../api/escenarios'
import type { MiSesion } from '../api/misSesiones'
import type { Usuario } from '../api/usuarios'
import { EditorEvidencia, EvidenciaSimulada } from '../components/Evidencia'
import { Lecciones } from '../components/Lecciones'
import { BibliotecaPage } from '../pages/BibliotecaPage'
import { LoginPage } from '../pages/LoginPage'
import { MisSesionesPage } from '../pages/MisSesionesPage'
import { ResumenDelParticipante } from '../pages/ResumenParticipante'
import { UsuariosPage } from '../pages/UsuariosPage'
import {
  ADMINISTRADOR,
  PARTICIPANTE,
  renderConSesion,
  respuesta,
  sesionDePrueba,
} from './utilidades'

async function violaciones(contenedor: Element = document.body) {
  const r = await axe.run(contenedor, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    rules: {
      // Sin CSS real en jsdom: el contraste se mide en el navegador.
      'color-contrast': { enabled: false },
      // Se renderizan fragmentos de página, no documentos completos.
      'html-has-lang': { enabled: false },
      'document-title': { enabled: false },
    },
  })
  return r.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
}

function simularApi(rutas: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const clave = Object.keys(rutas).find((r) => url.includes(r))
      return respuesta(200, clave ? rutas[clave] : [])
    }),
  )
}

const USUARIOS: Usuario[] = [
  {
    id: 'u1',
    nombre: 'Ana López',
    correo: 'ana@demo.test',
    rol: 'participante',
    activo: true,
    creado_en: '2026-10-16T10:00:00Z',
  },
  {
    id: 'u2',
    nombre: 'Luis Pérez',
    correo: 'luis@demo.test',
    rol: 'moderador',
    activo: false,
    creado_en: '2026-10-16T10:00:00Z',
  },
]

const ESCENARIOS: EscenarioResumen[] = [
  {
    id: 'e1',
    nombre: 'Ransomware en servidores de archivos',
    tipo_codigo: 'ransomware',
    nivel: 'alto',
    estado: 'publicado',
    roles: ['ti', 'legal'],
    total_injects: 4,
    total_tareas: 8,
  },
]

const MIS_SESIONES: MiSesion[] = [
  {
    id: 's1',
    nombre: 'Simulacro Q4',
    estado: 'programada',
    fecha_programada: '2026-12-01T15:00:00Z',
    duracion_minutos: 90,
    escenario_nombre: 'Ransomware',
    escenario_descripcion: 'Cifrado de servidores',
    moderador_nombre: 'Mónica',
    rol_codigo: 'ti',
    rol_nombre: 'Responsable de TI',
    total_participantes: 5,
    invitacion: 'enviada',
    invitacion_aceptada_en: null,
  },
  {
    id: 's2',
    nombre: 'Simulacro Q3',
    estado: 'finalizada',
    fecha_programada: '2026-09-01T15:00:00Z',
    duracion_minutos: 60,
    escenario_nombre: 'Phishing',
    escenario_descripcion: 'Robo de credenciales',
    moderador_nombre: 'Mónica',
    rol_codigo: 'ti',
    rol_nombre: 'Responsable de TI',
    total_participantes: 4,
    invitacion: 'aceptada',
    invitacion_aceptada_en: '2026-08-30T10:00:00Z',
  },
]

const RESUMEN: ResumenParticipante = {
  sesion_id: 's2',
  nombre: 'Simulacro Q3',
  finalizada_en: '2026-09-01T16:00:00Z',
  rol_nombre: 'Responsable de TI',
  puntaje: 7.5,
  maximo: 10,
  porcentaje: 75,
  posicion: 2,
  total_participantes: 4,
  tareas: [
    {
      inject_orden: 1,
      inject_titulo: 'Detección',
      enunciado: '¿Qué aísla primero?',
      tipo: 'texto_libre',
      puntaje_maximo: 10,
      respondida: true,
      respuesta: 'La red de servidores',
      puntaje: 7.5,
      aciertos: ['Aislar la red'],
      faltantes: ['Preservar evidencia'],
      errores: [],
      opciones_correctas: [],
      ajuste_motivo: 'Buena priorización',
    },
  ],
  lecciones: {
    fortalezas: ['Escalaron rápido'],
    mejoras: ['Probar respaldos'],
    acciones: [
      {
        descripcion: 'Simulacro trimestral',
        prioridad: 'alta',
        rol_codigo: null,
        plazo: '2026-12-15',
        responsable: 'Toda la organización',
      },
    ],
  },
}

describe('Accesibilidad WCAG 2.1 AA (axe-core)', () => {
  it('inicio de sesión', async () => {
    renderConSesion(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>,
      { sesion: sesionDePrueba(null), ruta: '/login' },
    )
    await screen.findByRole('button', { name: 'Ingresar' })
    expect(await violaciones()).toEqual([])
  })

  it('gestión de usuarios', async () => {
    simularApi({ '/usuarios': USUARIOS })
    renderConSesion(<UsuariosPage />, { sesion: sesionDePrueba(ADMINISTRADOR) })
    await screen.findByText('Luis Pérez')
    expect(await violaciones()).toEqual([])
  })

  it('biblioteca de escenarios con filtros', async () => {
    simularApi({ '/escenarios': ESCENARIOS })
    renderConSesion(<BibliotecaPage />, { sesion: sesionDePrueba(ADMINISTRADOR) })
    await screen.findByText('Ransomware en servidores de archivos')
    expect(await violaciones()).toEqual([])
  })

  it('mis sesiones del participante (próximas y finalizadas)', async () => {
    simularApi({ '/mis-sesiones': MIS_SESIONES })
    renderConSesion(<MisSesionesPage />, { sesion: sesionDePrueba(PARTICIPANTE) })
    await screen.findByText('Simulacro Q3')
    expect(await violaciones()).toEqual([])
  })

  it('resumen del participante con retroalimentación y lecciones', async () => {
    simularApi({ '/resumen': RESUMEN })
    renderConSesion(<ResumenDelParticipante sesionId="s2" />, {
      sesion: sesionDePrueba(PARTICIPANTE),
    })
    await screen.findByText('Tu resultado como Responsable de TI')
    expect(await violaciones()).toEqual([])
  })

  it('control: la auditoría sí detecta un campo sin etiqueta', async () => {
    const { container } = render(
      <main>
        <input type="text" />
        <button type="button" />
      </main>,
    )
    const encontradas = await violaciones(container)
    expect(encontradas.some((v) => v.startsWith('label:'))).toBe(true)
    expect(encontradas.some((v) => v.startsWith('button-name:'))).toBe(true)
  })

  it('las 6 evidencias simuladas, su editor y las lecciones', async () => {
    const { container } = render(
      <main>
        {(['correo', 'alerta', 'noticia', 'llamada', 'mensaje', 'documento'] as const).map(
          (tipo) => (
            <EvidenciaSimulada
              key={tipo}
              evidencia={{
                tipo,
                origen: 'Origen ficticio',
                asunto: 'Asunto',
                contenido: 'Contenido',
                nivel: tipo === 'alerta' ? 'critica' : null,
              }}
            />
          ),
        )}
        <EditorEvidencia
          valor={{ tipo: 'alerta', origen: '', asunto: '', contenido: '', nivel: 'alta' }}
          onChange={() => {}}
        />
        <Lecciones {...RESUMEN.lecciones!} />
      </main>,
    )
    expect(await violaciones(container)).toEqual([])
  })
})
