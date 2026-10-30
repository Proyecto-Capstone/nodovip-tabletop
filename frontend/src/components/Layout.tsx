import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { nombreRolSistema, useSesion } from '../auth/sesionContext'

export function Layout() {
  const {
    usuario,
    cerrarSesion,
    puedeLeerEscenarios,
    puedeGestionarEscenarios,
    puedeGestionarUsuarios,
    puede,
  } = useSesion()
  const navegar = useNavigate()
  const [saliendo, setSaliendo] = useState(false)

  const salir = async () => {
    setSaliendo(true)
    try {
      await cerrarSesion()
    } finally {
      navegar('/login', { replace: true })
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="marca">NODOVIP — Plataforma Tabletop Exercise</span>
        {usuario && (
          <div className="usuario-barra">
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

      <nav className="sidebar" aria-label="Navegación principal">
        {puedeLeerEscenarios && (
          <>
            <NavLink to="/escenarios" end>
              Biblioteca de escenarios
            </NavLink>
            <NavLink to="/banco-preguntas">Banco de preguntas</NavLink>
          </>
        )}
        {puedeGestionarEscenarios && (
          <NavLink to="/escenarios/nuevo">Nuevo escenario</NavLink>
        )}
        {puede('sesiones:disenar') && <NavLink to="/sesiones">Mis tabletops</NavLink>}
        {puede('sesiones:participar') && (
          <NavLink to="/mis-sesiones">Mis sesiones</NavLink>
        )}
        {puede('leaderboard:ver') && <NavLink to="/leaderboard">Leaderboard</NavLink>}
        {puede('sesiones:monitorear') && <NavLink to="/monitoreo">Monitoreo</NavLink>}
        {puede('reportes:ver') && <NavLink to="/reportes">Reportes</NavLink>}
        {puedeGestionarUsuarios && (
          <>
            <NavLink to="/usuarios">Gestión de usuarios</NavLink>
            <NavLink to="/accesos">Historial de accesos</NavLink>
          </>
        )}
      </nav>

      <main className="contenido">
        <Outlet />
      </main>
    </div>
  )
}
