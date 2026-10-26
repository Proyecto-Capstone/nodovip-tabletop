import type { EstadoEscenario, Nivel } from '../api/escenarios'
import type { EstadoInvitacion, EstadoSesion } from '../api/sesiones'
import {
  ETIQUETA_ESTADO,
  ETIQUETA_ESTADO_SESION,
  ETIQUETA_INVITACION,
  ETIQUETA_NIVEL,
} from '../lib/etiquetas'

export function NivelBadge({ nivel }: { nivel: Nivel }) {
  return <span className={`badge nivel-${nivel}`}>{ETIQUETA_NIVEL[nivel]}</span>
}

export function EstadoBadge({ estado }: { estado: EstadoEscenario }) {
  return (
    <span className={`badge estado-${estado}`}>{ETIQUETA_ESTADO[estado]}</span>
  )
}

export function EstadoSesionBadge({ estado }: { estado: EstadoSesion }) {
  return (
    <span className={`badge sesion-${estado}`}>{ETIQUETA_ESTADO_SESION[estado]}</span>
  )
}

export function InvitacionBadge({ estado }: { estado: EstadoInvitacion }) {
  return (
    <span className={`badge invitacion-${estado}`}>{ETIQUETA_INVITACION[estado]}</span>
  )
}

export function Cargando() {
  return <p className="texto-suave">Cargando…</p>
}

export function Errores({ errores }: { errores?: string[] }) {
  if (!errores?.length) return null
  return (
    <div className="alerta alerta-error" role="alert">
      {errores.length === 1 ? (
        errores[0]
      ) : (
        <ul>
          {errores.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function SinPermiso() {
  return (
    <div className="alerta alerta-aviso" role="alert">
      Sin acceso: tu rol no tiene permiso para esta sección. Si crees que es un
      error, pide al administrador que revise tu rol.
    </div>
  )
}
