import type { EstadoEscenario, Nivel } from '../api/escenarios'
import { ETIQUETA_ESTADO, ETIQUETA_NIVEL } from '../lib/etiquetas'

export function NivelBadge({ nivel }: { nivel: Nivel }) {
  return <span className={`badge nivel-${nivel}`}>{ETIQUETA_NIVEL[nivel]}</span>
}

export function EstadoBadge({ estado }: { estado: EstadoEscenario }) {
  return (
    <span className={`badge estado-${estado}`}>{ETIQUETA_ESTADO[estado]}</span>
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
    <div className="alerta alerta-aviso">
      Tu rol no tiene acceso a esta sección. Cambia el rol en la barra superior.
    </div>
  )
}
