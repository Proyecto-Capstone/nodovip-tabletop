// Insignia de estado en vivo de una sesión (PB-07), compartida entre el panel
// del moderador (ConducirSesionPage) y el monitoreo de solo lectura (PC-24).

import { Circle, Pause } from 'lucide-react'

export function EstadoVivo({ estado, pausada }: { estado: string; pausada: boolean }) {
  if (estado === 'en_curso' && pausada) {
    return (
      <span className="badge badge-pausa">
        <Pause size={12} aria-hidden="true" /> En pausa
      </span>
    )
  }
  if (estado === 'en_curso') {
    return (
      <span className="badge badge-live">
        <Circle size={10} fill="currentColor" aria-hidden="true" /> EN VIVO
      </span>
    )
  }
  if (estado === 'finalizada') return <span className="badge sesion-finalizada">Finalizada</span>
  return <span className="badge sesion-programada">Programada</span>
}
