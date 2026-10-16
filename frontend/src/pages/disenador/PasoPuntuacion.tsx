// Paso 4: pesos de evaluación (RF-03) y puntaje máximo de cada tarea (CU-03.4).

import { useId } from 'react'
import type { Pesos } from '../../api/sesiones'
import { nombreRol } from '../../lib/etiquetas'
import { ETIQUETA_TIPO_TAREA, sumaPesos, type PropsPaso } from './comun'

const ASPECTOS: { clave: keyof Pesos; nombre: string; ayuda: string }[] = [
  { clave: 'completitud', nombre: 'Completitud', ayuda: 'Cubre los criterios esperados' },
  { clave: 'precision', nombre: 'Precisión', ayuda: 'La respuesta es correcta' },
  { clave: 'tiempo', nombre: 'Tiempo', ayuda: 'Responde antes del límite' },
]

export function PasoPuntuacion({ d, cambiar, roles }: PropsPaso) {
  const id = useId()
  const suma = sumaPesos(d)
  const total = d.tareas.reduce((s, t) => s + t.puntaje_maximo, 0)

  return (
    <>
      <section className="tarjeta">
        <h2>Pesos de la evaluación automática</h2>
        <p className="texto-suave">
          Cómo se reparte el puntaje de cada respuesta. Deben sumar 100 %. Una
          respuesta fuera de tiempo recibe cero.
        </p>
        <div className="fila-campos">
          {ASPECTOS.map((a) => (
            <div key={a.clave} className="campo">
              <label htmlFor={`${id}-${a.clave}`}>{a.nombre} (%)</label>
              <input
                id={`${id}-${a.clave}`}
                aria-describedby={`${id}-${a.clave}-ayuda`}
                type="number"
                min={0}
                max={100}
                value={d.pesos[a.clave]}
                onChange={(e) =>
                  cambiar((x) => ({
                    ...x,
                    pesos: { ...x.pesos, [a.clave]: Number(e.target.value) },
                  }))
                }
              />
              <small id={`${id}-${a.clave}-ayuda`} className="texto-suave">
                {a.ayuda}
              </small>
            </div>
          ))}
        </div>
        <p className={suma === 100 ? 'suma-pesos ok' : 'suma-pesos texto-peligro'}>
          Suma: {suma} %{suma !== 100 && ' — debe ser 100 %'}
        </p>
      </section>

      <section className="tarjeta tabla-contenedor">
        <table className="tabla">
          <thead>
            <tr>
              <th>Rol</th>
              <th>Inject</th>
              <th>Tarea</th>
              <th>Tipo</th>
              <th className="sin-salto">Puntaje máximo</th>
            </tr>
          </thead>
          <tbody>
            {d.tareas.map((t) => {
              const n = d.injects.findIndex((i) => i.id === t.inject_id)
              return (
                <tr key={t.id}>
                  <td className="sin-salto">{nombreRol(roles, t.rol_codigo)}</td>
                  <td className="sin-salto">{n < 0 ? '—' : n + 1}</td>
                  <td>{t.enunciado}</td>
                  <td className="sin-salto">{ETIQUETA_TIPO_TAREA[t.tipo]}</td>
                  <td>
                    <input
                      className="input-puntaje"
                      type="number"
                      min={1}
                      max={100}
                      aria-label={`Puntaje máximo: ${t.enunciado}`}
                      value={t.puntaje_maximo}
                      onChange={(e) =>
                        cambiar((x) => ({
                          ...x,
                          tareas: x.tareas.map((y) =>
                            y.id === t.id
                              ? { ...y, puntaje_maximo: Number(e.target.value) }
                              : y,
                          ),
                        }))
                      }
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={4}>
                <strong>Puntuación máxima posible</strong> (se calcula sola)
              </td>
              <td>
                <strong data-testid="puntaje-total">{total}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </section>
    </>
  )
}
