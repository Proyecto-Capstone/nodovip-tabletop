// PB-11: secciones del panel del moderador que muestran el avance de la sesión.
// Los datos llegan de /puntajes y /respuestas, que el panel recarga cada vez que
// el WebSocket avisa de una respuesta nueva o cambia el inject.

import { Link } from 'react-router-dom'
import type { Inject } from '../api/escenarios'
import type { PuntajeRol, RespuestaRegistrada } from '../api/respuestas'
import type { Participante } from '../api/sesiones'

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

const formatoHora = (iso: string) =>
  new Date(iso).toLocaleTimeString('es-EC', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

export function AvancePorRol({
  roles,
  participantes,
  conectados,
}: {
  roles: PuntajeRol[]
  participantes: Participante[]
  conectados: Set<string>
}) {
  return (
    <section className="tarjeta" aria-labelledby="titulo-avance-rol">
      <h2 id="titulo-avance-rol">Avance por rol</h2>
      {roles.length === 0 ? (
        <p className="texto-suave">Sin roles en la sesión.</p>
      ) : (
        <ul className="avance-roles">
          {roles.map((r) => {
            const delRol = participantes.filter((p) => p.rol_codigo === r.rol_codigo)
            const enLinea = delRol.filter((p) => conectados.has(p.usuario_id)).length
            const esperadas = r.respondidas + r.sin_responder
            const avance = esperadas ? (100 * r.respondidas) / esperadas : 0
            return (
              <li key={r.rol_codigo}>
                <div className="avance-rol-cabecera">
                  <strong>{r.rol_nombre}</strong>
                  <span className="texto-suave">
                    {enLinea}/{delRol.length} conectados
                  </span>
                </div>
                <div
                  className="barra-avance"
                  role="progressbar"
                  aria-label={`Respuestas de ${r.rol_nombre}`}
                  aria-valuenow={Math.round(avance)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <span style={{ width: `${avance}%` }} />
                </div>
                <div className="avance-rol-datos texto-suave">
                  <span>
                    {esperadas === 0
                      ? 'Sin tareas lanzadas'
                      : `${r.respondidas} de ${esperadas} respuestas · ${r.sin_responder} pendientes`}
                  </span>
                  <span>
                    <strong>{formatoPuntaje(r.puntaje)}</strong> / {r.maximo} pts
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export function InjectsLanzados({ injects, actual }: { injects: Inject[]; actual: number }) {
  return (
    <section className="tarjeta" aria-labelledby="titulo-injects">
      <h2 id="titulo-injects">Injects</h2>
      <ol className="lista-injects-vivo">
        {[...injects]
          .sort((a, b) => a.orden - b.orden)
          .map((i) => {
            const estado =
              i.orden < actual ? 'lanzado' : i.orden === actual ? 'actual' : 'pendiente'
            return (
              <li key={i.id} className={`inject-${estado}`}>
                <span className="inject-marca" aria-hidden="true">
                  {estado === 'lanzado' ? '✓' : estado === 'actual' ? '●' : i.orden}
                </span>
                <span>
                  {i.titulo}
                  {i.minuto_sugerido !== null && (
                    <span className="texto-suave"> · min {i.minuto_sugerido}</span>
                  )}
                </span>
                <span className="texto-suave">
                  {estado === 'lanzado'
                    ? 'Lanzado'
                    : estado === 'actual'
                      ? 'En curso'
                      : 'Pendiente'}
                </span>
              </li>
            )
          })}
      </ol>
    </section>
  )
}

export function UltimasRespuestas({
  sesionId,
  respuestas,
}: {
  sesionId: string
  respuestas: RespuestaRegistrada[]
}) {
  const ultimas = respuestas.slice(-5).reverse()
  return (
    <section className="tarjeta" aria-labelledby="titulo-ultimas">
      <div className="encabezado-seccion">
        <h2 id="titulo-ultimas">Últimas respuestas</h2>
        <Link to={`/sesiones/${sesionId}/respuestas`}>Ver todas ({respuestas.length})</Link>
      </div>
      {ultimas.length === 0 ? (
        <p className="texto-suave">Todavía no llegan respuestas.</p>
      ) : (
        <ul className="ultimas-respuestas">
          {ultimas.map((r) => (
            <li key={r.id}>
              <span className="texto-suave sin-salto">{formatoHora(r.recibida_en)}</span>
              <span>
                <strong>{r.participante_nombre}</strong>
                <span className="texto-suave">
                  {' '}
                  · {r.rol_nombre} · Inject {r.inject_orden}
                </span>
              </span>
              <span className="sin-salto">
                {formatoPuntaje(r.puntaje)} / {r.puntaje_maximo}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
