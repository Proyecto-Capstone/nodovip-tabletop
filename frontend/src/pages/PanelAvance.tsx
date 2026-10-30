// PB-11: secciones del panel del moderador (prototipo P-05, Figura 20).
// Los datos llegan de /puntajes y /respuestas, que el panel recarga cada vez que
// el WebSocket avisa de una respuesta nueva o cambia el inject.

import { useEffect, useState } from 'react'
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

/** Estado de un participante frente a las tareas ya lanzadas de su rol. */
function estadoProgreso(respondidas: number, esperadas: number) {
  if (esperadas === 0) return { clase: 'progreso-espera', texto: 'Sin tareas aún' }
  if (respondidas >= esperadas) return { clase: 'progreso-respondido', texto: 'Respondido' }
  if (respondidas > 0) return { clase: 'progreso-curso', texto: 'En progreso' }
  return { clase: 'progreso-sin', texto: 'Sin respuesta' }
}

export interface FilaProgreso {
  usuarioId: string
  nombre: string
  rolNombre: string
  conectado: boolean
  respondidas: number
  esperadas: number
}

export function ProgresoParticipantes({
  filas,
  injectActual,
}: {
  filas: FilaProgreso[]
  injectActual: number
}) {
  return (
    <section className="tarjeta" aria-labelledby="titulo-progreso">
      <h2 id="titulo-progreso">
        Progreso por participante{injectActual > 0 ? ` — Inject ${injectActual}` : ''}
      </h2>
      <ul className="progreso-participantes">
        {filas.map((f) => {
          const avance = f.esperadas ? Math.round((100 * f.respondidas) / f.esperadas) : 0
          const estado = estadoProgreso(f.respondidas, f.esperadas)
          return (
            <li key={f.usuarioId}>
              <span className="progreso-persona">
                <span className="progreso-nombre">
                  <span
                    className={f.conectado ? 'punto conectado' : 'punto'}
                    title={f.conectado ? 'Conectado' : 'Sin conexión'}
                  />
                  <strong>{f.nombre}</strong>
                </span>
                <span className="texto-suave">
                  {f.rolNombre} · {f.conectado ? 'Conectado' : 'Sin conexión'}
                </span>
              </span>
              <div
                className={`barra-avance barra-${estado.clase}`}
                role="progressbar"
                aria-label={`Avance de ${f.nombre}`}
                aria-valuenow={avance}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${avance}%` }} />
              </div>
              <span className="texto-suave progreso-porcentaje">{avance}%</span>
              <span className={`badge ${estado.clase}`}>{estado.texto}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/** Extracto de la respuesta: el texto o las opciones elegidas. */
function extracto(r: RespuestaRegistrada, largo = 110) {
  const contenido = r.texto ?? r.opciones_elegidas_texto.join(', ')
  return contenido.length > largo ? `${contenido.slice(0, largo).trimEnd()}…` : contenido
}

export function RespuestasRecientes({
  sesionId,
  respuestas,
}: {
  sesionId: string
  respuestas: RespuestaRegistrada[]
}) {
  const recientes = respuestas.slice(-5).reverse()
  return (
    <section className="respuestas-recientes" aria-labelledby="titulo-recientes">
      <div className="encabezado-seccion">
        <h3 id="titulo-recientes">Respuestas recientes</h3>
        {respuestas.length > 0 && (
          <Link to={`/sesiones/${sesionId}/respuestas`}>Ver todas ({respuestas.length})</Link>
        )}
      </div>
      {recientes.length === 0 ? (
        <p className="texto-suave">Todavía no llegan respuestas.</p>
      ) : (
        <ul>
          {recientes.map((r) => (
            <li key={r.id}>
              <div className="respuesta-reciente-cabecera">
                <strong>
                  {r.participante_nombre} — {r.rol_nombre}
                </strong>
                <span className="texto-suave sin-salto">{formatoHora(r.recibida_en)}</span>
              </div>
              <p className="texto-suave">{extracto(r)}</p>
              <span className="texto-suave">
                Inject {r.inject_orden} · {formatoPuntaje(r.puntaje)} / {r.puntaje_maximo} pts
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** "Lanzado hace 02:14 minutos", y se actualiza cada segundo. */
export function LanzadoHace({ desde }: { desde: string }) {
  const segundos = useSegundosDesde(desde)
  const m = String(Math.floor(segundos / 60)).padStart(2, '0')
  const s = String(segundos % 60).padStart(2, '0')
  return (
    <p className="texto-suave lanzado-hace">
      Lanzado hace {m}:{s} minutos
    </p>
  )
}

function useSegundosDesde(iso: string) {
  const [ahora, setAhora] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return Math.max(0, Math.floor((ahora - Date.parse(iso)) / 1000))
}
