// Anillo de avance en SVG con el porcentaje al centro (decorativo: el dato se
// muestra también como texto junto al anillo).

export function Anillo({ porcentaje, className }: { porcentaje: number; className?: string }) {
  const radio = 22
  const circunferencia = 2 * Math.PI * radio
  const acotado = Math.max(0, Math.min(100, porcentaje))
  return (
    <svg className={`anillo ${className ?? ''}`} viewBox="0 0 56 56" aria-hidden="true">
      <circle className="anillo-pista" cx="28" cy="28" r={radio} />
      <circle
        className="anillo-avance"
        cx="28"
        cy="28"
        r={radio}
        strokeDasharray={circunferencia}
        strokeDashoffset={circunferencia * (1 - acotado / 100)}
      />
      <text x="28" y="28" dominantBaseline="central" textAnchor="middle">
        {acotado}%
      </text>
    </svg>
  )
}
