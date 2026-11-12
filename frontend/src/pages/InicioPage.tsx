// Página de entrada después del login: cada rol va a su primera sección útil.

import { Navigate } from 'react-router-dom'
import { useSesion } from '../auth/sesionContext'

export function InicioPage() {
  const { puedeLeerEscenarios, puede } = useSesion()

  if (puedeLeerEscenarios) return <Navigate to="/escenarios" replace />
  if (puede('sesiones:participar')) return <Navigate to="/mis-sesiones" replace />
  if (puede('reportes:ver')) return <Navigate to="/reportes" replace />

  // Último rol posible: Observador.
  return <Navigate to="/leaderboard" replace />
}
