import type { ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Permiso } from '../api/auth'
import { useSesion } from '../auth/sesionContext'
import { SinPermiso } from './Etiquetas'

/**
 * Sin sesión redirige a /login y recuerda a dónde quería ir el usuario.
 * Con `permiso`, si el rol no lo tiene muestra "Sin acceso" en vez de la página.
 * El backend valida igual cada request: esto solo evita pantallas vacías.
 */
export function RutaProtegida({
  permiso,
  children,
}: {
  permiso?: Permiso
  children?: ReactNode
}) {
  const { usuario, cargando, puede } = useSesion()
  const ubicacion = useLocation()

  if (cargando) {
    return (
      <p className="pantalla-carga" role="status">
        Cargando…
      </p>
    )
  }
  if (!usuario) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ desde: ubicacion.pathname + ubicacion.search }}
      />
    )
  }
  if (permiso && !puede(permiso)) return <SinPermiso />
  return children ?? <Outlet />
}
