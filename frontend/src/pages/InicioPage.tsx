// Página de entrada después del login: cada rol va a su primera sección útil.

import { Navigate } from 'react-router-dom'
import { nombreRolSistema, useSesion } from '../auth/sesionContext'

export function InicioPage() {
  const { usuario, puedeLeerEscenarios } = useSesion()

  if (puedeLeerEscenarios) return <Navigate to="/escenarios" replace />

  // Participante, Observador y Analista: sus pantallas llegan en los
  // sprints 3 a 5 (vista de participante, leaderboard y reportes).
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
