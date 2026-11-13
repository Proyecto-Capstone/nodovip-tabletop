// Tarjeta de indicador (KPI): ícono con el tono del estado, etiqueta, valor
// grande y un detalle opcional. La usan la biblioteca y el leaderboard.

import type { ReactNode } from 'react'

export type Tono = 'azul' | 'verde' | 'naranja' | 'rojo' | 'gris' | 'senal'

export function Indicador({
  icono,
  etiqueta,
  valor,
  detalle,
  tono,
}: {
  icono: ReactNode
  etiqueta: string
  valor: ReactNode
  detalle?: string
  tono: Tono
}) {
  return (
    <div className={`indicador indicador-${tono}`}>
      <span className="indicador-icono" aria-hidden="true">
        {icono}
      </span>
      <div>
        <p className="indicador-etiqueta">{etiqueta}</p>
        <p className="indicador-valor">{valor}</p>
        {detalle && <p className="indicador-detalle">{detalle}</p>}
      </div>
    </div>
  )
}
