// Opciones de una pregunta de selección múltiple: texto y si es correcta.
// Lo usan el formulario del escenario (PC-46) y el diseñador de la sesión (PB-05).

import type { Opcion } from '../api/sesiones'

const MAX_OPCIONES = 8

export function EditorOpciones({
  opciones,
  onChange,
}: {
  opciones: Opcion[]
  onChange: (opciones: Opcion[]) => void
}) {
  const cambiar = (indice: number, cambios: Partial<Opcion>) =>
    onChange(opciones.map((o, i) => (i === indice ? { ...o, ...cambios } : o)))

  return (
    <fieldset className="bloque">
      <legend>Opciones (marca las correctas)</legend>
      {opciones.map((o, i) => (
        <div key={i} className="fila-opcion">
          <input
            type="checkbox"
            aria-label={`Opción ${i + 1} correcta`}
            checked={o.correcta}
            onChange={(e) => cambiar(i, { correcta: e.target.checked })}
          />
          <input
            aria-label={`Texto de la opción ${i + 1}`}
            maxLength={300}
            value={o.texto}
            onChange={(e) => cambiar(i, { texto: e.target.value })}
          />
          <button
            type="button"
            className="boton boton-texto texto-peligro"
            aria-label={`Quitar opción ${i + 1}`}
            onClick={() => onChange(opciones.filter((_, x) => x !== i))}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="boton boton-texto"
        disabled={opciones.length >= MAX_OPCIONES}
        onClick={() => onChange([...opciones, { texto: '', correcta: false }])}
      >
        + Agregar opción
      </button>
    </fieldset>
  )
}
