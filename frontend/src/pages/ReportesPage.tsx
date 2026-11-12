// PB-14: sesiones finalizadas con su reporte de brechas (Analista, Moderador y
// Administrador). El Moderador solo ve las suyas. Lista a la izquierda y, a la
// derecha, la vista previa del reporte elegido (se carga solo ese detalle).

import {
  AlertTriangle,
  ArrowRight,
  Building2,
  ChevronRight,
  Clock,
  Download,
  FileCheck2,
  FileText,
  FileWarning,
  RefreshCw,
  Search,
  Users,
} from 'lucide-react'
import { useMemo, useRef, useState, type Ref } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  regenerarPdf,
  rutasReportes,
  type EstadoReporte,
  type Reporte,
  type SesionConReporte,
  type Severidad,
} from '../api/reportes'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { Indicador } from '../components/Indicador'
import { Medidor } from '../components/Medidor'
import { nivelDePorcentaje } from '../lib/niveles'
import { useGet } from '../lib/useGet'

type Filtro = 'todos' | 'con_cliente' | 'sin_cliente'

const FILTROS: { valor: Filtro; texto: string }[] = [
  { valor: 'todos', texto: 'Todos' },
  { valor: 'con_cliente', texto: 'Clientes' },
  { valor: 'sin_cliente', texto: 'Sin cliente' },
]

const ETIQUETA_SEVERIDAD: Record<Severidad, string> = {
  alta: 'altas',
  media: 'medias',
  baja: 'bajas',
}

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

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

function formatoDuracion(segundos: number | null) {
  if (segundos === null) return '—'
  const minutos = Math.round(segundos / 60)
  return minutos < 60 ? `${minutos} min` : `${Math.floor(minutos / 60)} h ${minutos % 60} min`
}

const normalizar = (texto: string) => texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

export function EstadoPdfBadge({ reporte }: { reporte: EstadoReporte | null }) {
  if (!reporte) return <span className="badge invitacion-pendiente">Sin generar</span>
  if (reporte.estado === 'generado') {
    return <span className="badge invitacion-aceptada">PDF listo</span>
  }
  if (reporte.estado === 'fallido') {
    return (
      <span className="badge invitacion-fallida" title={reporte.error ?? undefined}>
        Falló el PDF
      </span>
    )
  }
  return <span className="badge invitacion-enviada">Generando…</span>
}

export function ReportesPage() {
  const { rol } = useSesion()
  const sesiones = useGet<SesionConReporte[]>(rutasReportes.lista, rol)
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [texto, setTexto] = useState('')
  const [elegido, setElegido] = useState<string | null>(null)
  const vistaRef = useRef<HTMLElement>(null)

  const lista = useMemo(() => sesiones.datos ?? [], [sesiones.datos])
  const visibles = useMemo(() => {
    const buscado = normalizar(texto.trim())
    return lista.filter(
      (s) =>
        (filtro === 'todos' || (filtro === 'con_cliente') === Boolean(s.cliente)) &&
        (!buscado ||
          normalizar(s.nombre).includes(buscado) ||
          normalizar(s.cliente ?? '').includes(buscado)),
    )
  }, [lista, filtro, texto])

  const seleccion = visibles.find((s) => s.id === elegido) ?? visibles[0]
  const listos = lista.filter((s) => s.reporte?.estado === 'generado').length
  const conProblema = lista.filter((s) => !s.reporte || s.reporte.estado === 'fallido').length
  const clientes = new Set(lista.map((s) => s.cliente?.trim().toLowerCase()).filter(Boolean)).size
  const conCliente = lista.filter((s) => s.cliente).length

  const elegir = (id: string) => {
    setElegido(id)
    if (window.matchMedia?.('(max-width: 1100px)')?.matches) {
      requestAnimationFrame(() =>
        vistaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    }
  }

  return (
    <div className="reportes">
      <div className="encabezado">
        <div>
          <h1>Reportes de brechas organizacionales</h1>
          <p className="texto-suave">
            Un reporte por cada sesión finalizada: nivel de madurez, brechas por rol, trazabilidad
            de respuestas y recomendaciones, con exportación a PDF.
          </p>
        </div>
      </div>

      <Errores errores={sesiones.errores} />
      {sesiones.cargando && <Cargando />}

      {sesiones.datos && lista.length === 0 && (
        <div className="tarjeta vacio">Todavía no hay sesiones finalizadas.</div>
      )}

      {lista.length > 0 && (
        <>
          <section className="indicadores" aria-label="Resumen de reportes">
            <Indicador
              tono="azul"
              icono={<FileText />}
              etiqueta="Reportes emitidos"
              valor={lista.length}
              detalle="Uno por sesión finalizada"
            />
            <Indicador
              tono="verde"
              icono={<FileCheck2 />}
              etiqueta="PDF listos"
              valor={listos}
              detalle="Listos para descargar"
            />
            <Indicador
              tono="naranja"
              icono={<FileWarning />}
              etiqueta="PDF pendientes"
              valor={conProblema}
              detalle="Sin generar o con error"
            />
            <Indicador
              tono="gris"
              icono={<Building2 />}
              etiqueta="Clientes evaluados"
              valor={clientes}
              detalle={`${conCliente} sesiones con cliente`}
            />
          </section>

          <div className="reportes-columnas">
            <section className="reportes-lista" aria-label="Sesiones finalizadas">
              <div className="segmentos" role="group" aria-label="Filtrar reportes">
                {FILTROS.map((f) => (
                  <button
                    key={f.valor}
                    type="button"
                    className="segmento"
                    aria-pressed={filtro === f.valor}
                    onClick={() => setFiltro(f.valor)}
                  >
                    {f.texto}
                  </button>
                ))}
              </div>
              <label className="campo">
                <span className="solo-lector">Buscar reporte</span>
                <span className="campo-icono">
                  <Search aria-hidden="true" />
                  <input
                    type="search"
                    placeholder="Buscar por sesión o cliente…"
                    value={texto}
                    maxLength={100}
                    onChange={(e) => setTexto(e.target.value)}
                  />
                </span>
              </label>
              <p className="texto-suave reportes-conteo" aria-live="polite">
                {visibles.length} {visibles.length === 1 ? 'reporte' : 'reportes'}
              </p>

              {visibles.length === 0 ? (
                <div className="vacio vacio-compacto">Ningún reporte coincide con la búsqueda.</div>
              ) : (
                <ul className="reportes-items">
                  {visibles.map((s) => {
                    const activo = seleccion?.id === s.id
                    return (
                      <li key={s.id}>
                        <button
                          type="button"
                          className={`reporte-item${activo ? ' activo' : ''}`}
                          aria-pressed={activo}
                          onClick={() => elegir(s.id)}
                        >
                          <span className="reporte-item-cabecera">
                            <strong>{s.nombre}</strong>
                            <EstadoPdfBadge reporte={s.reporte} />
                          </span>
                          <span className="reporte-item-cliente">
                            {s.cliente ?? <span className="texto-suave">Sin cliente</span>}
                          </span>
                          <span className="reporte-item-meta">
                            <span>
                              <Clock aria-hidden="true" />
                              {formatoFecha(s.finalizada_en)}
                            </span>
                            <span>
                              <Users aria-hidden="true" />
                              {s.participantes} participantes
                            </span>
                          </span>
                          <ChevronRight className="reporte-item-flecha" aria-hidden="true" />
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </section>

            {seleccion && (
              <VistaPrevia
                key={seleccion.id}
                ref={vistaRef}
                sesion={seleccion}
                alRegenerar={sesiones.recargar}
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}

function VistaPrevia({
  sesion,
  alRegenerar,
  ref,
}: {
  sesion: SesionConReporte
  alRegenerar: () => void
  ref: Ref<HTMLElement>
}) {
  const { rol } = useSesion()
  const detalle = useGet<Reporte>(rutasReportes.reporte(sesion.id), rol)
  const [regenerando, setRegenerando] = useState(false)
  const [errores, setErrores] = useState<string[]>()
  const r = detalle.datos

  const regenerar = async () => {
    setRegenerando(true)
    setErrores(undefined)
    try {
      await regenerarPdf(sesion.id)
      detalle.recargar()
      alRegenerar()
    } catch (e) {
      setErrores(e instanceof ApiError ? e.errores : ['Error de conexión'])
    } finally {
      setRegenerando(false)
    }
  }

  const cuantas = (s: Severidad) => r?.brechas.filter((b) => b.severidad === s).length ?? 0
  const pdfListo = (r?.pdf ?? sesion.reporte)?.estado === 'generado'

  return (
    <aside ref={ref} className="tarjeta reporte-vista" aria-labelledby="titulo-vista-previa">
      <p className="reporte-vista-rotulo">Vista previa del reporte</p>
      <div className="reporte-vista-cabecera">
        <div>
          <h2 id="titulo-vista-previa">{sesion.nombre}</h2>
          {r && <p className="texto-suave">{r.escenario}</p>}
        </div>
        <div className="reporte-vista-acciones">
          {pdfListo ? (
            <a
              className="boton boton-primario boton-destacado"
              href={rutasReportes.pdf(sesion.id)}
              download
            >
              <Download size={16} aria-hidden="true" /> Descargar PDF
            </a>
          ) : (
            <button
              type="button"
              className="boton boton-primario boton-destacado"
              disabled={regenerando}
              onClick={regenerar}
            >
              <RefreshCw size={16} aria-hidden="true" />
              {regenerando ? 'Generando…' : 'Generar PDF'}
            </button>
          )}
          <Link className="boton boton-secundario" to={`/reportes/${sesion.id}`}>
            Ver reporte completo <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </div>

      <Errores errores={errores ?? detalle.errores} />
      {!r && !detalle.errores && <Cargando />}

      {r && (
        <>
          <div className="reporte-vista-resumen">
            <dl className="reporte-vista-datos">
              <div>
                <dt>Cliente</dt>
                <dd>{r.cliente ?? 'Sin cliente'}</dd>
              </div>
              <div>
                <dt>Finalizada</dt>
                <dd>{formatoFecha(r.finalizada_en)}</dd>
              </div>
              <div>
                <dt>Moderador</dt>
                <dd>{r.moderador}</dd>
              </div>
              <div>
                <dt>Duración</dt>
                <dd>{formatoDuracion(r.duracion_segundos)}</dd>
              </div>
            </dl>
            <div className="reporte-vista-madurez">
              <p>Nivel de madurez</p>
              <Medidor porcentaje={r.porcentaje_total} etiqueta="Nivel de madurez" />
              <p className="texto-suave">
                {formatoPuntaje(r.puntaje_total)} / {r.maximo_total} pts
              </p>
            </div>
            <div className="reporte-vista-severidad">
              <p>Severidad de brechas</p>
              {r.brechas.length === 0 ? (
                <span className="badge severidad-baja">Sin brechas</span>
              ) : (
                <div className="chips">
                  {(['alta', 'media', 'baja'] as const)
                    .filter((s) => cuantas(s) > 0)
                    .map((s) => (
                      <span key={s} className={`badge severidad-${s}`}>
                        {cuantas(s)} {ETIQUETA_SEVERIDAD[s]}
                      </span>
                    ))}
                </div>
              )}
              <p className="texto-suave">
                {r.injects_lanzados}/{r.total_injects} injects · {r.respuestas.length} respuestas
              </p>
            </div>
          </div>

          <section className="reporte-vista-seccion" aria-labelledby="titulo-vista-roles">
            <h3 id="titulo-vista-roles">Brechas detectadas por rol organizacional</h3>
            <ul className="reporte-vista-roles">
              {r.por_rol.map((f) => {
                const brechasRol = r.brechas.filter((b) => b.rol_nombre === f.nombre)
                const nivel = nivelDePorcentaje(f.porcentaje)
                return (
                  <li key={f.nombre}>
                    <span className="reporte-vista-rol-cabecera">
                      <strong>{f.nombre}</strong>
                      <span className={`texto-${nivel}`}>
                        {formatoPuntaje(f.puntaje)} / {f.maximo} pts
                      </span>
                    </span>
                    <span className={`reporte-barra tier-${nivel}`} aria-hidden="true">
                      <span style={{ width: `${f.porcentaje}%` }} />
                    </span>
                    <span className="texto-suave">
                      {brechasRol.length === 0 ? (
                        'Sin brechas en este rol.'
                      ) : (
                        <>
                          <AlertTriangle size={13} aria-hidden="true" /> {brechasRol.length}{' '}
                          {brechasRol.length === 1 ? 'brecha' : 'brechas'}:{' '}
                          {brechasRol[0].tipo_etiqueta.toLowerCase()}
                        </>
                      )}
                    </span>
                  </li>
                )
              })}
            </ul>
          </section>

          {r.recomendaciones.length > 0 && (
            <section className="reporte-vista-seccion" aria-labelledby="titulo-vista-recs">
              <h3 id="titulo-vista-recs">Recomendaciones principales</h3>
              <ol className="reporte-vista-recs">
                {r.recomendaciones.slice(0, 3).map((x, i) => (
                  <li key={i}>
                    <span className={`badge severidad-${x.prioridad}`}>{x.rol_nombre}</span>
                    <span>{x.texto}</span>
                  </li>
                ))}
              </ol>
              {r.recomendaciones.length > 3 && (
                <Link className="enlace-mas" to={`/reportes/${sesion.id}#recomendaciones`}>
                  Ver las {r.recomendaciones.length} recomendaciones
                </Link>
              )}
            </section>
          )}

          <p className="reporte-vista-pie">
            <EstadoPdfBadge reporte={r.pdf} />
            {r.pdf?.generado_en
              ? `PDF generado el ${formatoFecha(r.pdf.generado_en)}`
              : 'El PDF se genera al cerrar la sesión o con «Generar PDF».'}
          </p>
        </>
      )}
    </aside>
  )
}
