// Secciones de la aplicación agrupadas como en el menú lateral, filtradas por
// los permisos del usuario. Las usan el menú y los accesos directos de Inicio.

import {
  Activity,
  CalendarCheck,
  ClipboardList,
  FileBarChart2,
  FilePlus,
  HelpCircle,
  History,
  Home,
  Library,
  Trophy,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useSesion } from '../auth/sesionContext'

export interface Enlace {
  to: string
  fin?: boolean
  texto: string
  /** Nombre breve para los accesos directos de Inicio. */
  corto?: string
  icono: LucideIcon
  mostrar: boolean
}

export interface GrupoNav {
  titulo: string
  enlaces: Enlace[]
}

export function useGruposNav(): GrupoNav[] {
  const { puedeLeerEscenarios, puedeGestionarEscenarios, puedeGestionarUsuarios, puede } =
    useSesion()

  return [
    {
      titulo: 'Operación',
      enlaces: [
        { to: '/', fin: true, texto: 'Inicio', icono: Home, mostrar: true },
        {
          to: '/sesiones',
          texto: 'Mis tabletops',
          corto: 'Tabletops',
          icono: ClipboardList,
          mostrar: puede('sesiones:disenar'),
        },
        {
          to: '/mis-sesiones',
          texto: 'Mis sesiones',
          corto: 'Mis sesiones',
          icono: CalendarCheck,
          mostrar: puede('sesiones:participar'),
        },
      ],
    },
    {
      titulo: 'Diseño',
      enlaces: [
        {
          to: '/escenarios',
          fin: true,
          texto: 'Biblioteca de escenarios',
          corto: 'Escenarios',
          icono: Library,
          mostrar: puedeLeerEscenarios,
        },
        {
          to: '/banco-preguntas',
          texto: 'Banco de preguntas',
          corto: 'Preguntas',
          icono: HelpCircle,
          mostrar: puedeLeerEscenarios,
        },
        {
          to: '/escenarios/nuevo',
          texto: 'Nuevo escenario',
          corto: 'Nuevo',
          icono: FilePlus,
          mostrar: puedeGestionarEscenarios,
        },
      ],
    },
    {
      titulo: 'Análisis',
      enlaces: [
        {
          to: '/leaderboard',
          texto: 'Leaderboard',
          icono: Trophy,
          mostrar: puede('leaderboard:ver'),
        },
        {
          to: '/monitoreo',
          texto: 'Monitoreo',
          icono: Activity,
          mostrar: puede('sesiones:monitorear'),
        },
        {
          to: '/reportes',
          texto: 'Reportes',
          icono: FileBarChart2,
          mostrar: puede('reportes:ver'),
        },
      ],
    },
    {
      titulo: 'Administración',
      enlaces: [
        {
          to: '/usuarios',
          texto: 'Gestión de usuarios',
          corto: 'Usuarios',
          icono: Users,
          mostrar: puedeGestionarUsuarios,
        },
        {
          to: '/accesos',
          texto: 'Historial de accesos',
          corto: 'Accesos',
          icono: History,
          mostrar: puedeGestionarUsuarios,
        },
      ],
    },
  ]
}
