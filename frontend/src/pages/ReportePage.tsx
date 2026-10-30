// PB-14: "Reporte de brechas" de una sesión finalizada, según el prototipo P-07
// (Figura 22): índice lateral, puntajes finales por rol, brechas por rol,
// trazabilidad de respuestas y recomendaciones, con exportación a PDF.

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  regenerarPdf,
  rutasReportes,
  type Brecha,
  type FilaPuntaje,
  type Reporte,
  type Severidad,
} from '../api/reportes'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'
import { EstadoPdfBadge } from './ReportesPage'

const SECCIONES = [
  ['resumen', '1. Resumen ejecutivo'],
  ['puntajes', '2. Puntajes finales'],
  ['brechas', '3. Brechas detectadas'],
  ['trazabilidad', '4. Trazabilidad'],
  ['recomendaciones', '5. Recomendaciones'],
] as const

const ETIQUETA_SEVERIDAD: Record<Severidad, string> = {
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
}

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

const formatoFecha = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString('es-EC', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'

const formatoHora = (iso: string) =>
  new Date(iso).toLocaleTimeString('es-EC', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

function formatoDuracion(segundos: number | null) {
  if (segundos === null) return '—'
  const dos = (n: number) => String(n).padStart(2, '0')
  return `${dos(Math.floor(segundos / 3600))}:${dos(Math.floor((segundos % 3600) / 60))}:${dos(segundos % 60)}`
}

const nivelDe = (porcentaje: number) =>
  porcentaje >= 70 ? 'verde' : porcentaje >= 40 ? 'naranja' : 'rojo'

export function ReportePage() {
  const { id = '' } = useParams()
  const { rol } = useSesion()
  const reporte = useGet<Reporte>(rutasReportes.reporte(id), rol)

  if (reporte.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        Reporte no disponible: la sesión no existe o todavía no ha finalizado.{' '}
        <Link to="/reportes">Ver reportes</Link>
      </div>
    )
  }
  if (reporte.errores) return <Errores errores={reporte.errores} />
  if (!reporte.datos) return <Cargando />
  return <Contenido r={reporte.datos} recargar={reporte.recargar} />
}

function Contenido({ r, recargar }: { r: Reporte; recargar: () => void }) {
  const [regenerando, setRegenerando] = useState(false)
  const [errores, setErrores] = useState<string[]>()

  const regenerar = async () => {
    setRegenerando(true)
    setErrores(undefined)
    try {
      await regenerarPdf(r.sesion_id)
      recargar()
    } catch (e) {
      setErrores(e instanceof ApiError ? e.errores : ['Error de conexión'])
    } finally {
      setRegenerando(false)
    }
  }

  return (
    <>
      <Link to="/reportes" className="volver">
        ← Reportes
      </Link>
      <div className="encabezado">
        <div>
          <h1>Reporte de cierre: {r.nombre}</h1>
          <p className="texto-suave">
            PDF: <EstadoPdfBadge reporte={r.pdf} />
            {r.pdf?.generado_en && ` · generado ${formatoFecha(r.pdf.generado_en)}`}
          </p>
        </div>
        <div className="acciones-fila">
          <button
            type="button"
            className="boton boton-texto"
            disabled={regenerando}
            onClick={regenerar}
          >
            {regenerando ? 'Generando…' : 'Regenerar PDF'}
          </button>
          <a className="boton boton-peligro" href={rutasReportes.pdf(r.sesion_id)} download>
            ⬇ Exportar PDF
          </a>
        </div>
      </div>
      <Errores errores={errores} />

      <div className="reporte-layout">
        <nav className="reporte-indice" aria-label="Contenido del reporte">
          <strong>Contenido del reporte</strong>
          {SECCIONES.map(([ancla, titulo]) => (
            <a key={ancla} href={`#${ancla}`}>
              {titulo}
            </a>
          ))}
        </nav>

        <div className="reporte-contenido">
          <Resumen r={r} />
          <section id="puntajes" className="tarjeta" aria-labelledby="titulo-puntajes">
            <h2 id="titulo-puntajes">Puntajes finales por rol</h2>
            <BarrasPuntaje filas={r.por_rol} />
            <h3>Por participante</h3>
            <TablaPuntajes filas={r.por_participante} />
          </section>
          <Brechas brechas={r.brechas} superadas={r.superadas} />
          <Trazabilidad r={r} />
          <section
            id="recomendaciones"
            className="tarjeta reporte-recomendaciones"
            aria-labelledby="titulo-recomendaciones"
          >
            <h2 id="titulo-recomendaciones">Recomendaciones principales</h2>
            <ol>
              {r.recomendaciones.map((x, i) => (
                <li key={i}>
                  <span className={`badge severidad-${x.prioridad}`}>
                    {ETIQUETA_SEVERIDAD[x.prioridad]}
                  </span>{' '}
                  <strong>{x.rol_nombre}:</strong> {x.texto}
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </>
  )
}

function Resumen({ r }: { r: Reporte }) {
  const cuantas = (s: Severidad) => r.brechas.filter((b) => b.severidad === s).length
  const recurrentes = r.brechas.filter((b) => b.recurrente_en > 0).length
  return (
    <section id="resumen" className="tarjeta" aria-labelledby="titulo-resumen">
      <h2 id="titulo-resumen">Reporte de Brechas Organizacionales</h2>
      <p className="texto-suave">
        {r.escenario} · Cliente: {r.cliente ?? 'sin cliente'} · Fecha: {formatoFecha(r.iniciada_en)}{' '}
        · Duración: {formatoDuracion(r.duracion_segundos)} · Moderador: {r.moderador} ·
        Participantes: {r.participantes}
      </p>
      <div className="metricas">
        <div className="tarjeta metrica">
          <strong className={`texto-${nivelDe(r.porcentaje_total)}`}>{r.porcentaje_total} %</strong>
          <span className="texto-suave">
            Puntaje global ({formatoPuntaje(r.puntaje_total)} / {r.maximo_total})
          </span>
        </div>
        <div className="tarjeta metrica">
          <strong>{r.brechas.length}</strong>
          <span className="texto-suave">
            Brechas: {cuantas('alta')} altas, {cuantas('media')} medias, {cuantas('baja')} bajas
          </span>
        </div>
        <div className="tarjeta metrica">
          <strong>
            {r.injects_lanzados}/{r.total_injects}
          </strong>
          <span className="texto-suave">Injects lanzados</span>
        </div>
        <div className="tarjeta metrica">
          <strong>{r.respuestas.length}</strong>
          <span className="texto-suave">Respuestas registradas</span>
        </div>
      </div>
      <p className="parrafo">
        {r.sesiones_anteriores > 0
          ? `${r.sesiones_anteriores === 1 ? 'Se comparó 1 sesión anterior' : `Se compararon ${r.sesiones_anteriores} sesiones anteriores`} del cliente: ${recurrentes} brechas se repiten y ${r.superadas.length} ya se superaron.`
          : r.cliente
            ? 'Es la primera sesión registrada de este cliente.'
            : 'La sesión no tiene cliente: no hay historial para comparar.'}
      </p>
    </section>
  )
}

function BarrasPuntaje({ filas }: { filas: FilaPuntaje[] }) {
  return (
    <ul className="reporte-barras">
      {filas.map((f) => (
        <li key={f.nombre}>
          <span>
            <strong>{f.nombre}</strong>
            <span className="texto-suave"> · {f.detalle}</span>
          </span>
          <div
            className={`reporte-barra tier-${nivelDe(f.porcentaje)}`}
            role="progressbar"
            aria-label={`Puntaje de ${f.nombre}`}
            aria-valuenow={Math.round(f.porcentaje)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <span style={{ width: `${f.porcentaje}%` }} />
          </div>
          <span className={`sin-salto texto-${nivelDe(f.porcentaje)}`}>
            <strong>{formatoPuntaje(f.puntaje)}</strong>
            <span className="texto-suave"> /{f.maximo}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}

function TablaPuntajes({ filas }: { filas: FilaPuntaje[] }) {
  return (
    <div className="tabla-contenedor">
      <table className="tabla">
        <thead>
          <tr>
            <th>Participante</th>
            <th>Puntaje</th>
            <th>Respondidas</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={`${f.nombre}-${f.detalle}`}>
              <td>
                {f.nombre}
                <div className="texto-suave">{f.detalle}</div>
              </td>
              <td className="sin-salto">
                {formatoPuntaje(f.puntaje)} / {f.maximo} ({f.porcentaje} %)
              </td>
              <td>
                {f.respondidas} de {f.respondidas + f.sin_responder}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Brechas({ brechas, superadas }: { brechas: Brecha[]; superadas: Brecha[] }) {
  return (
    <section id="brechas" className="tarjeta" aria-labelledby="titulo-brechas">
      <h2 id="titulo-brechas">Brechas detectadas por rol</h2>
      {brechas.length === 0 ? (
        <p className="texto-suave">No se detectaron brechas en esta sesión.</p>
      ) : (
        <div className="tabla-contenedor">
          <table className="tabla tabla-brechas">
            <thead>
              <tr>
                <th>Rol</th>
                <th>Tarea</th>
                <th>Tipo de brecha</th>
                <th>Severidad</th>
                <th>Inject</th>
              </tr>
            </thead>
            <tbody>
              {brechas.map((b, i) => (
                <tr key={i}>
                  <td>
                    <strong>{b.rol_nombre}</strong>
                    <div className="texto-suave">{b.participante}</div>
                  </td>
                  <td>
                    {b.tarea}
                    {b.detalle.length > 0 && (
                      <div className="texto-suave">{b.detalle.slice(0, 3).join('; ')}</div>
                    )}
                  </td>
                  <td>
                    {b.tipo_etiqueta}
                    <div className="texto-suave">{b.porcentaje} %</div>
                    {b.recurrente_en > 0 && (
                      <div className="texto-peligro">Recurrente ({b.recurrente_en})</div>
                    )}
                  </td>
                  <td>
                    <span className={`badge severidad-${b.severidad}`}>
                      {ETIQUETA_SEVERIDAD[b.severidad]}
                    </span>
                  </td>
                  <td className="sin-salto">Inject {b.inject_orden}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {superadas.length > 0 && (
        <>
          <h3>Superadas respecto a la sesión anterior del cliente</h3>
          <ul>
            {superadas.map((b, i) => (
              <li key={i}>
                {b.rol_nombre}: «{b.tarea}»
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function Trazabilidad({ r }: { r: Reporte }) {
  return (
    <section id="trazabilidad" className="tarjeta" aria-labelledby="titulo-trazabilidad">
      <h2 id="titulo-trazabilidad">Trazabilidad de respuestas</h2>
      <p className="texto-suave">
        Hora del servidor al recibir cada respuesta. Las respuestas son inmutables; los ajustes de
        puntaje quedan registrados.
      </p>
      {r.respuestas.length === 0 ? (
        <p className="texto-suave">No hubo respuestas.</p>
      ) : (
        <div className="tabla-contenedor">
          <table className="tabla tabla-respuestas">
            <thead>
              <tr>
                <th>Hora</th>
                <th>Participante</th>
                <th>Tarea</th>
                <th>Respuesta</th>
                <th>Puntaje</th>
              </tr>
            </thead>
            <tbody>
              {r.respuestas.map((x, i) => (
                <tr key={i}>
                  <td className="sin-salto">{formatoHora(x.recibida_en)}</td>
                  <td>
                    {x.participante}
                    <div className="texto-suave">{x.rol_nombre}</div>
                  </td>
                  <td>
                    <div className="texto-suave sin-salto">Inject {x.inject_orden}</div>
                    {x.tarea}
                  </td>
                  <td className="respuesta-registrada">{x.contenido}</td>
                  <td className="sin-salto">
                    {formatoPuntaje(x.puntaje)} / {x.puntaje_maximo}
                    {x.ajustada && <div className="texto-suave">ajustado</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
