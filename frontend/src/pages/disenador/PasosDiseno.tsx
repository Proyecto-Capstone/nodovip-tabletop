// Barra lateral con los 6 pasos del diseñador, como en el prototipo (Figura 18).

import { PASOS } from './comun'

export function PasosDiseno({
  actual,
  completos,
  alElegir,
}: {
  actual: number
  completos: boolean[]
  alElegir?: (paso: number) => void
}) {
  return (
    <nav className="pasos-diseno" aria-label="Pasos del diseño">
      <p className="pasos-titulo">Pasos del diseño</p>
      <ol>
        {PASOS.map((nombre, i) => {
          const paso = i + 1
          const clase = [
            'paso',
            paso === actual ? 'actual' : '',
            completos[i] && paso !== actual ? 'completo' : '',
          ].join(' ')
          const contenido = (
            <>
              <span className="paso-numero" aria-hidden="true">
                {completos[i] && paso !== actual ? '✓' : paso}
              </span>
              {nombre}
            </>
          )
          return (
            <li key={nombre}>
              {alElegir ? (
                <button
                  type="button"
                  className={clase}
                  aria-current={paso === actual ? 'step' : undefined}
                  onClick={() => alElegir(paso)}
                >
                  {contenido}
                </button>
              ) : (
                <span className={clase} aria-current={paso === actual ? 'step' : undefined}>
                  {contenido}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
