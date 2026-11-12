import { useEffect, useState } from 'react'
import {
  Activity,
  CalendarCheck,
  ChevronRight,
  ClipboardList,
  FileBarChart2,
  FilePlus,
  HelpCircle,
  History,
  Home,
  Library,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Trophy,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import logoNodovip from '../assets/marca/nodovip-horizontal-claro.webp'
import { nombreRolSistema, useSesion } from '../auth/sesionContext'
import { ProveedorConfirmacion } from './DialogoConfirmacion'

const CLAVE_SIDEBAR = 'nodovip_sidebar_colapsado'

function leerSidebarGuardado(): boolean {
  try {
    return localStorage.getItem(CLAVE_SIDEBAR) === 'si'
  } catch {
    return false
  }
}

function guardarSidebar(colapsado: boolean) {
  try {
    localStorage.setItem(CLAVE_SIDEBAR, colapsado ? 'si' : 'no')
  } catch {
    // Sin almacenamiento disponible (navegación privada): el estado no
    // persiste entre visitas, pero el menú sigue funcionando en esta.
  }
}

interface Enlace {
  to: string
  fin?: boolean
  texto: string
  icono: LucideIcon
  mostrar: boolean
}

interface GrupoNav {
  titulo: string
  enlaces: Enlace[]
}

function useGruposNav(): GrupoNav[] {
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
          icono: ClipboardList,
          mostrar: puede('sesiones:disenar'),
        },
        {
          to: '/mis-sesiones',
          texto: 'Mis sesiones',
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
          icono: Library,
          mostrar: puedeLeerEscenarios,
        },
        {
          to: '/banco-preguntas',
          texto: 'Banco de preguntas',
          icono: HelpCircle,
          mostrar: puedeLeerEscenarios,
        },
        {
          to: '/escenarios/nuevo',
          texto: 'Nuevo escenario',
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
          icono: Users,
          mostrar: puedeGestionarUsuarios,
        },
        {
          to: '/accesos',
          texto: 'Historial de accesos',
          icono: History,
          mostrar: puedeGestionarUsuarios,
        },
      ],
    },
  ]
}

/** Migas de pan para páginas internas; las pantallas de primer nivel (las que
 * ya están en el menú) no llevan migas. */
function useMigas(): { grupo: string; titulo: string } | null {
  const { pathname } = useLocation()

  if (/^\/escenarios\/nuevo$/.test(pathname)) return { grupo: 'Diseño', titulo: 'Nuevo escenario' }
  if (/^\/escenarios\/[^/]+\/editar$/.test(pathname)) {
    return { grupo: 'Diseño', titulo: 'Editar escenario' }
  }
  if (/^\/escenarios\/[^/]+$/.test(pathname)) {
    return { grupo: 'Diseño', titulo: 'Detalle del escenario' }
  }
  if (/^\/sesiones\/nueva$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Nueva sesión' }
  }
  if (/^\/sesiones\/[^/]+\/disenar$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Diseñar sesión' }
  }
  if (/^\/sesiones\/[^/]+\/conducir$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Conducir sesión' }
  }
  if (/^\/sesiones\/[^/]+\/respuestas$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Respuestas de la sesión' }
  }
  if (/^\/sesiones\/[^/]+\/debrief$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Debrief' }
  }
  if (/^\/reportes\/[^/]+$/.test(pathname)) {
    return { grupo: 'Análisis', titulo: 'Reporte de brechas' }
  }
  if (/^\/leaderboard\/[^/]+$/.test(pathname)) {
    return { grupo: 'Análisis', titulo: 'Leaderboard de la sesión' }
  }
  if (/^\/monitoreo\/[^/]+$/.test(pathname)) {
    return { grupo: 'Análisis', titulo: 'Monitoreo de la sesión' }
  }
  if (/^\/mis-sesiones\/[^/]+\/en-vivo$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Sesión en vivo' }
  }
  if (/^\/mis-sesiones\/[^/]+$/.test(pathname)) {
    return { grupo: 'Operación', titulo: 'Mi sesión' }
  }
  return null
}

export function Layout() {
  const { usuario, cerrarSesion } = useSesion()
  const navegar = useNavigate()
  const { pathname } = useLocation()
  const [colapsado, setColapsado] = useState(leerSidebarGuardado)
  const [cajonAbierto, setCajonAbierto] = useState(false)
  const [saliendo, setSaliendo] = useState(false)
  const grupos = useGruposNav()
  const migas = useMigas()

  // Cierra el cajón al navegar (clic en un enlace, atrás/adelante del
  // navegador, etc.): se ajusta durante el render, no en un efecto, como
  // recomienda React para "resetear estado cuando cambia algo externo".
  const [rutaAnterior, setRutaAnterior] = useState(pathname)
  if (pathname !== rutaAnterior) {
    setRutaAnterior(pathname)
    if (cajonAbierto) setCajonAbierto(false)
  }

  useEffect(() => {
    if (!cajonAbierto) return
    const alTeclado = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') setCajonAbierto(false)
    }
    document.addEventListener('keydown', alTeclado)
    return () => document.removeEventListener('keydown', alTeclado)
  }, [cajonAbierto])

  const alternarColapso = () => {
    setColapsado((actual) => {
      guardarSidebar(!actual)
      return !actual
    })
  }

  const salir = async () => {
    setSaliendo(true)
    try {
      await cerrarSesion()
    } finally {
      navegar('/login', { replace: true })
    }
  }

  return (
    <ProveedorConfirmacion>
      <div
        className={`app ${colapsado ? 'sidebar-colapsado' : ''} ${
          cajonAbierto ? 'sidebar-abierto' : ''
        }`}
      >
        {/* PC-47 (WCAG 2.4.1): con teclado se salta el menú y se va al contenido. */}
        <a className="saltar-contenido" href="#contenido">
          Saltar al contenido
        </a>
        <header className="topbar">
          <div className="topbar-izquierda">
            <button
              type="button"
              className="boton-hamburguesa"
              aria-label={cajonAbierto ? 'Cerrar menú' : 'Abrir menú'}
              aria-expanded={cajonAbierto}
              onClick={() => setCajonAbierto((a) => !a)}
            >
              {cajonAbierto ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
            </button>
            <NavLink to="/" className="marca" aria-label="NODOVIP Tabletop, ir al inicio">
              <img src={logoNodovip} alt="" width={720} height={206} />
              <span className="marca-producto" aria-hidden="true">
                Tabletop
              </span>
            </NavLink>
          </div>
          {usuario && (
            <div className="menu-usuario">
              <span
                className="avatar"
                aria-hidden="true"
                title={`${usuario.nombre} · ${nombreRolSistema(usuario.rol)}`}
              >
                {iniciales(usuario.nombre)}
              </span>
              <span className="usuario-datos">
                <strong>{usuario.nombre}</strong>
                <span className="usuario-rol">{nombreRolSistema(usuario.rol)}</span>
              </span>
              <button
                type="button"
                className="boton boton-salir"
                onClick={salir}
                disabled={saliendo}
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </header>

        {cajonAbierto && <div className="velo-cajon" onClick={() => setCajonAbierto(false)} />}

        <nav className="sidebar" aria-label="Navegación principal">
          {grupos.map((grupo) => {
            const visibles = grupo.enlaces.filter((e) => e.mostrar)
            if (visibles.length === 0) return null
            return (
              <div className="sidebar-grupo" key={grupo.titulo}>
                <p className="sidebar-grupo-titulo">{grupo.titulo}</p>
                {visibles.map(({ to, fin, texto, icono: Icono }) => (
                  <NavLink key={to} to={to} end={fin} title={texto}>
                    <Icono size={18} aria-hidden="true" />
                    <span className={colapsado ? 'solo-lector' : undefined}>{texto}</span>
                  </NavLink>
                ))}
              </div>
            )
          })}
          <div className="sidebar-pie">
            <button
              type="button"
              className="sidebar-colapsar"
              onClick={alternarColapso}
              title={colapsado ? 'Expandir menú' : 'Colapsar menú'}
            >
              {colapsado ? (
                <PanelLeftOpen size={18} aria-hidden="true" />
              ) : (
                <PanelLeftClose size={18} aria-hidden="true" />
              )}
              <span className={colapsado ? 'solo-lector' : undefined}>
                {colapsado ? 'Expandir' : 'Colapsar'}
              </span>
            </button>
          </div>
        </nav>

        <main className="contenido" id="contenido" tabIndex={-1}>
          {migas && <Migas grupo={migas.grupo} titulo={migas.titulo} />}
          <Outlet />
        </main>
      </div>
    </ProveedorConfirmacion>
  )
}

/** Hasta dos iniciales del nombre, para el avatar del menú de usuario. */
function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean)
  return (
    (partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')
  ).toUpperCase()
}

function Migas({ grupo, titulo }: { grupo: string; titulo: string }) {
  return (
    <nav className="migas" aria-label="Ruta de navegación">
      <span>{grupo}</span>
      <ChevronRight size={14} aria-hidden="true" />
      <span aria-current="page">{titulo}</span>
    </nav>
  )
}
