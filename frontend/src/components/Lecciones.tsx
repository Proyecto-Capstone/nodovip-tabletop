// Lecciones aprendidas del debrief (PC-45): fortalezas, aspectos a mejorar y
// plan de acción. Se usa en el reporte, en el debrief completado y en el
// resumen del participante.

import { ETIQUETA_PRIORIDAD, formatoPlazo, type PrioridadAccion } from '../api/debrief'

interface Accion {
  descripcion: string
  responsable: string
  prioridad: PrioridadAccion | string
  plazo: string | null
}

export interface LeccionesProps {
  fortalezas: string[]
  mejoras: string[]
  acciones: Accion[]
}

export function Lecciones({ fortalezas, mejoras, acciones }: LeccionesProps) {
  return (
    <div className="lecciones">
      <div className="lecciones-columnas">
        <div className="lecciones-bloque lecciones-fortalezas">
          <h3>
            <span aria-hidden="true">✓</span> Fortalezas
          </h3>
          <ul>
            {fortalezas.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
        <div className="lecciones-bloque lecciones-mejoras">
          <h3>
            <span aria-hidden="true">↗</span> Aspectos a mejorar
          </h3>
          <ul>
            {mejoras.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      </div>
      {acciones.length > 0 && (
        <>
          <h3>Plan de acción</h3>
          <div className="tabla-contenedor">
            <table className="tabla">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Acción</th>
                  <th>Responsable</th>
                  <th>Prioridad</th>
                  <th>Plazo</th>
                </tr>
              </thead>
              <tbody>
                {acciones.map((a, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{a.descripcion}</td>
                    <td>{a.responsable}</td>
                    <td>
                      <span className={`badge severidad-${a.prioridad}`}>
                        {ETIQUETA_PRIORIDAD[a.prioridad as PrioridadAccion] ?? a.prioridad}
                      </span>
                    </td>
                    <td className="sin-salto">{formatoPlazo(a.plazo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
