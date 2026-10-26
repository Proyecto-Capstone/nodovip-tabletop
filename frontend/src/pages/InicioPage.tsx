// Página de entrada después del login: cada rol va a su primera sección útil.

import { Navigate } from 'react-router-dom'
import { nombreRolSistema, useSesion } from '../auth/sesionContext'

export function InicioPage() {
  const { usuario, puedeLeerEscenarios, puede } = useSesion()

  if (puedeLeerEscenarios) return <Navigate to="/escenarios" replace />
  if (puede('sesiones:participar')) return <Navigate to="/mis-sesiones" replace />

  // Observador y Analista: sus pantallas llegan en los sprints 4 y 5
  // (leaderboard y reportes).
  return (
    <div className="tarjeta">
      <h1>Hola, {usuario?.nombre}</h1>
      <p className="parrafo">
        Ingresaste como <strong>{usuario && nombreRolSistema(usuario.rol)}</strong>.
        Las secciones de tu rol estarán disponibles aquí cuando el moderador te
        invite a una sesión tabletop.
      </p>
    </div>
  )
}
