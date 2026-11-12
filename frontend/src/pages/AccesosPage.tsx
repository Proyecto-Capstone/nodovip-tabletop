// PB-01 / RNF-01: historial de accesos (usuario, fecha/hora, IP, resultado).
// Registro de eventos a la izquierda e inspector del evento elegido a la
// derecha. Todo sale de lo que ya registra el backend: no se geolocaliza ni
// se consulta ningún servicio externo.

import {
  Activity,
  Ban,
  Bot,
  CheckCircle2,
  Download,
  ExternalLink,
  Globe,
  Monitor,
  Search,
  ShieldAlert,
  XCircle,
} from 'lucide-react'
import { useMemo, useRef, useState, type Ref } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { rutaAccesos, type Acceso } from '../api/accesos'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { Indicador } from '../components/Indicador'
import {
  GRUPO_DE,
  RIESGO,
  aCsv,
  actividadPorHora,
  esIpInterna,
  leerAgente,
  type GrupoResultado,
} from '../lib/accesos'
import { ETIQUETA_RESULTADO } from '../lib/etiquetas'
import { useDebounce, useGet } from '../lib/useGet'

type Filtro = 'todos' | GrupoResultado

const FILTROS: { valor: Filtro; texto: string }[] = [
  { valor: 'todos', texto: 'Todos' },
  { valor: 'exitoso', texto: 'Exitosos' },
  { valor: 'fallido', texto: 'Fallidos' },
  { valor: 'bloqueado', texto: 'Bloqueados' },
]

const formatoFechaHora = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString('es-EC', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '—'

const formatoHora = (fecha: Date) =>
  fecha.toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' })

/** "2026-10-15" del input date → inicio o fin de ese día en hora local, en ISO. */
const limiteDelDia = (fecha: string, fin: boolean) =>
  fecha ? new Date(`${fecha}T${fin ? '23:59:59.999' : '00:00:00'}`).toISOString() : undefined

export function AccesosPage() {
  const { rol } = useSesion()
  const [parametros, setParametros] = useSearchParams()
  const usuarioId = parametros.get('usuario') ?? undefined
  const [texto, setTexto] = useState('')
  const [filtro, setFiltro] = useState<Filtro>('todos')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [elegido, setElegido] = useState<number | null>(null)
  const inspectorRef = useRef<HTMLElement>(null)
  const q = useDebounce(texto.trim())

  const accesos = useGet<Acceso[]>(
    rutaAccesos({
      usuario_id: usuarioId,
      q,
      desde: limiteDelDia(desde, false),
      hasta: limiteDelDia(hasta, true),
    }),
    rol,
  )

  const lista = useMemo(() => accesos.datos ?? [], [accesos.datos])
  const visibles = useMemo(
    () => (filtro === 'todos' ? lista : lista.filter((a) => GRUPO_DE[a.resultado] === filtro)),
    [lista, filtro],
  )
  const horas = useMemo(() => actividadPorHora(lista), [lista])

  const cuantos = (grupo: GrupoResultado) =>
    lista.filter((a) => GRUPO_DE[a.resultado] === grupo).length
  const exitosos = cuantos('exitoso')
  const fallidos = cuantos('fallido')
  const bloqueados = cuantos('bloqueado')
  const porcentaje = lista.length ? Math.round((exitosos / lista.length) * 100) : 0
  const maximoHora = Math.max(1, ...horas.map((h) => h.exitoso + h.fallido + h.bloqueado))
  const seleccion = visibles.find((a) => a.id === elegido) ?? visibles[0]
  const hayFiltros = Boolean(texto || desde || hasta || usuarioId || filtro !== 'todos')

  const limpiar = () => {
    setTexto('')
    setFiltro('todos')
    setDesde('')
    setHasta('')
    setParametros({})
  }

  const exportar = () => {
    const url = URL.createObjectURL(new Blob([aCsv(visibles)], { type: 'text/csv;charset=utf-8' }))
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = `accesos-${new Date().toISOString().slice(0, 10)}.csv`
    enlace.click()
    URL.revokeObjectURL(url)
  }

  const elegir = (id: number) => {
    setElegido(id)
    if (window.matchMedia?.('(max-width: 1100px)')?.matches) {
      requestAnimationFrame(() =>
        inspectorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    }
  }

  return (
    <div className="accesos">
      <div className="encabezado">
        <div>
          <h1>Auditoría y registro de accesos</h1>
          <p className="texto-suave">
            Cada intento de inicio de sesión, exitoso o no. Se muestran los 200 más recientes que
            cumplan los filtros.
          </p>
        </div>
        <button
          type="button"
          className="boton boton-primario boton-destacado"
          disabled={visibles.length === 0}
          onClick={exportar}
        >
          <Download size={16} aria-hidden="true" />
          Exportar CSV
        </button>
      </div>

      {usuarioId && (
        <div className="alerta alerta-aviso">
          Mostrando solo los accesos de un usuario. <Link to="/accesos">Ver todos</Link>
        </div>
      )}

      {accesos.datos && (
        <section className="indicadores" aria-label="Resumen de accesos">
          <Indicador
            tono="azul"
            icono={<Activity />}
            etiqueta="Eventos registrados"
            valor={lista.length}
            detalle="Con los filtros de búsqueda y fecha"
          />
          <Indicador
            tono="verde"
            icono={<CheckCircle2 />}
            etiqueta="Accesos exitosos"
            valor={
              <>
                {exitosos} <small className="indicador-sufijo">({porcentaje} %)</small>
              </>
            }
          />
          <Indicador
            tono="naranja"
            icono={<XCircle />}
            etiqueta="Intentos fallidos"
            valor={fallidos}
            detalle="Credenciales inválidas o cuenta inactiva"
          />
          <Indicador
            tono="rojo"
            icono={<Ban />}
            etiqueta="Bloqueos"
            valor={bloqueados}
            detalle="Tras 5 fallos en 15 minutos"
          />
        </section>
      )}

      {lista.length > 0 && (
        <section className="tarjeta actividad-accesos" aria-labelledby="titulo-actividad">
          <div className="actividad-cabecera">
            <h2 id="titulo-actividad">Actividad de las últimas 24 horas</h2>
            <ul className="actividad-leyenda" aria-hidden="true">
              <li className="exitoso">Exitosos</li>
              <li className="fallido">Fallidos</li>
              <li className="bloqueado">Bloqueos</li>
            </ul>
          </div>
          <div
            className="actividad-barras"
            role="img"
            aria-label={`Eventos por hora: ${
              horas
                .filter((h) => h.exitoso + h.fallido + h.bloqueado > 0)
                .map((h) => `${formatoHora(h.inicio)}, ${h.exitoso + h.fallido + h.bloqueado}`)
                .join('; ') || 'sin eventos'
            }`}
          >
            {horas.map((h, i) => {
              const total = h.exitoso + h.fallido + h.bloqueado
              return (
                <div
                  key={i}
                  className="actividad-columna"
                  title={`${formatoHora(h.inicio)} · ${total} eventos`}
                >
                  <span
                    className="actividad-pila"
                    style={{ height: `${(total / maximoHora) * 100}%` }}
                  >
                    {h.bloqueado > 0 && (
                      <span className="bloqueado" style={{ flexGrow: h.bloqueado }} />
                    )}
                    {h.fallido > 0 && <span className="fallido" style={{ flexGrow: h.fallido }} />}
                    {h.exitoso > 0 && <span className="exitoso" style={{ flexGrow: h.exitoso }} />}
                  </span>
                  {i % 3 === 0 && <span className="actividad-hora">{formatoHora(h.inicio)}</span>}
                </div>
              )
            })}
          </div>
        </section>
      )}

      <div className="barra-herramientas barra-accesos">
        <div className="segmentos" role="group" aria-label="Filtrar por resultado">
          {FILTROS.map((f) => (
            <button
              key={f.valor}
              type="button"
              className="segmento"
              aria-pressed={filtro === f.valor}
              onClick={() => setFiltro(f.valor)}
            >
              {f.texto}
              <span className="segmento-contador">
                {f.valor === 'todos' ? lista.length : cuantos(f.valor)}
              </span>
            </button>
          ))}
        </div>
        <div className="filtros-accesos">
          <label className="campo campo-busqueda-compacta">
            <span className="solo-lector">Buscar por correo</span>
            <span className="campo-icono">
              <Search aria-hidden="true" />
              <input
                type="search"
                placeholder="Buscar por correo…"
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
              />
            </span>
          </label>
          <label className="campo campo-fecha">
            <span className="solo-lector">Desde</span>
            <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          </label>
          <label className="campo campo-fecha">
            <span className="solo-lector">Hasta</span>
            <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          </label>
          {hayFiltros && (
            <button type="button" className="boton boton-texto" onClick={limpiar}>
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      <Errores errores={accesos.errores} />
      {accesos.cargando && !accesos.datos && <Cargando />}

      {accesos.datos && visibles.length === 0 && (
        <div className="tarjeta vacio">No hay accesos con esos filtros.</div>
      )}

      {visibles.length > 0 && (
        <div className="accesos-columnas">
          <section className="tarjeta registro-eventos" aria-labelledby="titulo-registro">
            <h2 id="titulo-registro">
              Registro de eventos <span className="contador">{visibles.length}</span>
            </h2>
            <ul className="lista-eventos">
              {visibles.map((a) => {
                const grupo = GRUPO_DE[a.resultado]
                const agente = leerAgente(a.user_agent)
                const activo = seleccion?.id === a.id
                return (
                  <li key={a.id}>
                    <button
                      type="button"
                      className={`evento-acceso evento-${grupo}${activo ? ' activo' : ''}`}
                      aria-pressed={activo}
                      onClick={() => elegir(a.id)}
                    >
                      <span className="evento-fecha">{formatoFechaHora(a.fecha_hora)}</span>
                      <span className={`badge acceso-${a.resultado}`}>
                        {ETIQUETA_RESULTADO[a.resultado]}
                      </span>
                      <span className="evento-correo">
                        {a.correo}
                        {!a.usuario_id && <small> (no registrado)</small>}
                      </span>
                      <span className="evento-ip">
                        {a.ip}
                        {esIpInterna(a.ip) && <small> · interna</small>}
                      </span>
                      <span className="evento-agente">
                        {agente.automatizado ? (
                          <Bot aria-hidden="true" />
                        ) : (
                          <Monitor aria-hidden="true" />
                        )}
                        {agente.navegador}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>

          {seleccion && <Inspector key={seleccion.id} ref={inspectorRef} acceso={seleccion} />}
        </div>
      )}
    </div>
  )
}

function Inspector({ acceso: a, ref }: { acceso: Acceso; ref: Ref<HTMLElement> }) {
  const [vista, setVista] = useState<'datos' | 'json'>('datos')
  const agente = leerAgente(a.user_agent)
  const riesgo = RIESGO[a.resultado]
  const interna = esIpInterna(a.ip)

  return (
    <aside ref={ref} className="tarjeta inspector-evento" aria-labelledby="titulo-inspector">
      <p className="reporte-vista-rotulo">Inspector de eventos</p>
      <h2 id="titulo-inspector">Intento de acceso #{a.id}</h2>
      <p className={`riesgo riesgo-${riesgo.nivel}`}>
        <ShieldAlert size={15} aria-hidden="true" />
        Riesgo estimado: {riesgo.texto}
      </p>

      <dl className="inspector-datos">
        <div>
          <dt>Fecha y hora</dt>
          <dd>{formatoFechaHora(a.fecha_hora)}</dd>
        </div>
        <div>
          <dt>Resultado</dt>
          <dd>
            <span className={`badge acceso-${a.resultado}`}>{ETIQUETA_RESULTADO[a.resultado]}</span>
          </dd>
        </div>
        <div>
          <dt>Correo ingresado</dt>
          <dd>
            {a.correo}
            <span className="texto-suave">
              {a.usuario_id ? ' · cuenta registrada' : ' · no corresponde a ninguna cuenta'}
            </span>
          </dd>
        </div>
        <div>
          <dt>Origen</dt>
          <dd>
            <Globe size={14} aria-hidden="true" /> {a.ip}
            <span className="texto-suave">{interna ? ' · red interna' : ' · red externa'}</span>
          </dd>
        </div>
      </dl>

      <div className="pestanas-inspector" role="tablist" aria-label="Vista del evento">
        <button
          type="button"
          role="tab"
          aria-selected={vista === 'datos'}
          className="segmento"
          onClick={() => setVista('datos')}
        >
          Navegador
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vista === 'json'}
          className="segmento"
          onClick={() => setVista('json')}
        >
          Registro JSON
        </button>
      </div>

      {vista === 'datos' ? (
        <div className="inspector-agente" role="tabpanel" aria-label="Navegador">
          <dl className="inspector-datos inspector-datos-compacto">
            <div>
              <dt>Navegador</dt>
              <dd>{agente.navegador}</dd>
            </div>
            <div>
              <dt>Sistema</dt>
              <dd>{agente.sistema}</dd>
            </div>
          </dl>
          {agente.automatizado && (
            <p className="alerta alerta-aviso">
              El intento vino de un script o de una herramienta de pruebas, no de un navegador.
            </p>
          )}
          <p className="inspector-ua">{a.user_agent ?? 'Sin user-agent'}</p>
        </div>
      ) : (
        <pre className="inspector-json" role="tabpanel" aria-label="Registro JSON" tabIndex={0}>
          {JSON.stringify(a, null, 2)}
        </pre>
      )}

      {a.usuario_id && (
        <Link
          className="boton boton-secundario boton-bloque"
          to={`/accesos?usuario=${a.usuario_id}`}
        >
          <ExternalLink size={15} aria-hidden="true" />
          Ver todos los accesos de esta cuenta
        </Link>
      )}
    </aside>
  )
}
