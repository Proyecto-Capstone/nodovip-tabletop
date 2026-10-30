// Paso 5: nombre, cliente, fecha, hora y duración de la sesión (CU-03.5).
// El cliente (PB-14) permite comparar el reporte con sus sesiones anteriores.

import type { SesionDetalle } from '../../api/sesiones'
import { aFechaLocal, desdeFechaLocal, formatoDuracion, type PropsPaso } from './comun'

const DURACIONES = [30, 45, 60, 90, 120, 180, 240]

export function PasoProgramar({
  d,
  cambiar,
  guardada,
}: PropsPaso & { guardada: SesionDetalle }) {
  return (
    <>
      <section className="tarjeta">
        <h2>Datos de la sesión</h2>
        <label className="campo">
          <span>Nombre de la sesión</span>
          <input
            required
            minLength={3}
            maxLength={150}
            value={d.nombre}
            onChange={(e) => cambiar((a) => ({ ...a, nombre: e.target.value }))}
          />
        </label>
        <label className="campo">
          <span>Cliente / organización (opcional)</span>
          <input
            maxLength={120}
            placeholder="Por ejemplo: Banco Andino"
            value={d.cliente ?? ''}
            onChange={(e) => cambiar((a) => ({ ...a, cliente: e.target.value || null }))}
          />
          <small className="texto-suave">
            El reporte de brechas compara con las sesiones anteriores del mismo cliente.
          </small>
        </label>
        <div className="fila-campos">
          <label className="campo">
            <span>Fecha y hora</span>
            <input
              type="datetime-local"
              value={aFechaLocal(d.fecha_programada)}
              onChange={(e) =>
                cambiar((a) => ({
                  ...a,
                  fecha_programada: desdeFechaLocal(e.target.value),
                }))
              }
            />
          </label>
          <label className="campo">
            <span>Duración</span>
            <select
              value={d.duracion_minutos ?? ''}
              onChange={(e) =>
                cambiar((a) => ({
                  ...a,
                  duracion_minutos: e.target.value ? Number(e.target.value) : null,
                }))
              }
            >
              <option value="">Elegir…</option>
              {DURACIONES.map((m) => (
                <option key={m} value={m}>
                  {formatoDuracion(m)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="tarjeta">
        <h2>Antes de programar</h2>
        {guardada.pendientes_para_programar.length === 0 ? (
          <p className="requisitos">
            <span className="ok">✓ La sesión cumple todas las reglas.</span>
          </p>
        ) : (
          <ul className="requisitos">
            {guardada.pendientes_para_programar.map((p) => (
              <li key={p} className="pendiente">
                <span aria-hidden="true">○</span> {p}
              </li>
            ))}
          </ul>
        )}
        <p className="texto-suave">
          Según lo último guardado. Al programar se guardan antes tus cambios.
        </p>
      </section>
    </>
  )
}
