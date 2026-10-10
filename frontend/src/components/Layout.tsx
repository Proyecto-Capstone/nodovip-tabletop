import { NavLink, Outlet } from 'react-router-dom'
import type { RolSistema } from '../api/client'
import { ROLES_SISTEMA, useRol } from '../auth/rolContext'

export function Layout() {
  const { rol, cambiarRol, esAdministrador } = useRol()

  return (
    <div className="app">
      <header className="topbar">
        <span className="marca">NODOVIP — Plataforma Tabletop Exercise</span>
        <label className="selector-rol" title="Temporal hasta que exista el login (PB-01)">
          <span>Rol (desarrollo)</span>
          <select
            value={rol}
            onChange={(e) => cambiarRol(e.target.value as RolSistema)}
          >
            {ROLES_SISTEMA.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.nombre}
              </option>
            ))}
          </select>
        </label>
      </header>

      <nav className="sidebar" aria-label="Navegación principal">
        <NavLink to="/escenarios" end>
          Biblioteca de escenarios
        </NavLink>
        <NavLink to="/banco-preguntas">Banco de preguntas</NavLink>
        {esAdministrador && (
          <>
            <NavLink to="/escenarios/nuevo">Nuevo escenario</NavLink>
            <NavLink to="/usuarios">Gestión de usuarios</NavLink>
          </>
        )}
      </nav>

      <main className="contenido">
        <Outlet />
      </main>
    </div>
  )
}
