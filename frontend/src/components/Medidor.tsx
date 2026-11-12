// Medidor semicircular (SVG) para un porcentaje, con el color según el nivel:
// verde ≥ 70 %, naranja ≥ 40 %, rojo por debajo. Es decorativo: el valor se
// anuncia con la etiqueta accesible del contenedor.

import { nivelDePorcentaje } from '../lib/niveles'

export function Medidor({ porcentaje, etiqueta }: { porcentaje: number; etiqueta: string }) {
  const acotado = Math.max(0, Math.min(100, porcentaje))
  const radio = 40
  const largo = Math.PI * radio
  return (
    <div
      className={`medidor medidor-${nivelDePorcentaje(acotado)}`}
      role="img"
      aria-label={`${etiqueta}: ${Math.round(acotado)} %`}
    >
      <svg viewBox="0 0 100 58" aria-hidden="true">
        <path className="medidor-pista" d="M 10 50 A 40 40 0 0 1 90 50" />
        <path
          className="medidor-avance"
          d="M 10 50 A 40 40 0 0 1 90 50"
          strokeDasharray={largo}
          strokeDashoffset={largo * (1 - acotado / 100)}
        />
      </svg>
      <span className="medidor-valor" aria-hidden="true">
        {Math.round(acotado)}%
      </span>
    </div>
  )
}
