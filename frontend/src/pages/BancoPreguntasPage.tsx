// RF-04 / PB-04: banco de preguntas reutilizable, por tipo, rol y dificultad.
// Lista agrupada a la izquierda y, a la derecha, la rúbrica de la pregunta
// elegida con una vista previa de cómo la ve el participante.

import {
  CheckCircle2,
  Circle,
  Clock,
  ExternalLink,
  ListChecks,
  MessageSquareText,
  Pencil,
  Search,
  Target,
} from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { rutas, type RolEjercicio, type TareaBanco, type TipoEscenario } from '../api/escenarios'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, NivelBadge, SinPermiso } from '../components/Etiquetas'
import { ETIQUETA_NIVEL, NIVELES, formatoTiempo, nombreRol, nombreTipo } from '../lib/etiquetas'
import { useGet } from '../lib/useGet'

type Agrupacion = 'escenario' | 'rol' | 'inject'

const ETIQUETA_AGRUPACION: Record<Agrupacion, string> = {
  escenario: 'Escenario',
  rol: 'Rol',
  inject: 'Momento del ejercicio',
}

interface Grupo {
  clave: string
  titulo: string
  detalle?: string
  preguntas: TareaBanco[]
}

const normalizar = (texto: string) => texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

export function BancoPreguntasPage() {
  const { rol, puedeLeerEscenarios, puedeGestionarEscenarios } = useSesion()
  const [tipo, setTipo] = useState('')
  const [rolFiltro, setRolFiltro] = useState('')
  const [dificultad, setDificultad] = useState('')
  const [texto, setTexto] = useState('')
  const [agrupacion, setAgrupacion] = useState<Agrupacion>('escenario')
  const [elegida, setElegida] = useState<string | null>(null)
  const panelRef = useRef<HTMLElement>(null)

  const habilitado = puedeLeerEscenarios
  const tipos = useGet<TipoEscenario[]>(habilitado ? rutas.tipos : null, rol)
  const roles = useGet<RolEjercicio[]>(habilitado ? rutas.roles : null, rol)
  const banco = useGet<TareaBanco[]>(
    habilitado ? rutas.banco({ tipo, rol: rolFiltro, dificultad }) : null,
    rol,
  )

  // La búsqueda por texto se hace en el navegador: el banco ya viene filtrado
  // por tipo, rol y dificultad, y son pocas decenas de preguntas.
  const visibles = useMemo(() => {
    const buscado = normalizar(texto.trim())
    const lista = banco.datos ?? []
    if (!buscado) return lista
    return lista.filter(
      (t) =>
        normalizar(t.enunciado).includes(buscado) ||
        normalizar(t.escenario_nombre).includes(buscado),
    )
  }, [banco.datos, texto])

  const grupos = useMemo<Grupo[]>(() => {
    const mapa = new Map<string, Grupo>()
    for (const t of visibles) {
      let clave: string
      let titulo: string
      let detalle: string | undefined
      if (agrupacion === 'escenario') {
        clave = t.escenario_id
        titulo = t.escenario_nombre
        detalle = nombreTipo(tipos.datos, t.tipo_codigo)
      } else if (agrupacion === 'rol') {
        clave = t.rol_codigo
        titulo = nombreRol(roles.datos, t.rol_codigo)
      } else {
        clave = t.inject_orden ? `i${t.inject_orden}` : 'sin'
        titulo = t.inject_orden ? `Inject ${t.inject_orden}` : 'Se reparte en orden'
        detalle = t.inject_orden ? 'Se pregunta al lanzar este inject' : undefined
      }
      if (!mapa.has(clave)) mapa.set(clave, { clave, titulo, detalle, preguntas: [] })
      mapa.get(clave)!.preguntas.push(t)
    }
    const lista = [...mapa.values()]
    if (agrupacion === 'inject') {
      lista.sort((a, b) =>
        a.clave === 'sin'
          ? 1
          : b.clave === 'sin'
            ? -1
            : a.clave.localeCompare(b.clave, undefined, { numeric: true }),
      )
    } else {
      lista.sort((a, b) => a.titulo.localeCompare(b.titulo, 'es'))
    }
    return lista
  }, [visibles, agrupacion, tipos.datos, roles.datos])

  if (!habilitado) return <SinPermiso />

  // En pantallas angostas la rúbrica queda debajo de la lista: se baja a ella.
  const elegir = (idPregunta: string) => {
    setElegida(idPregunta)
    if (window.matchMedia?.('(max-width: 1100px)')?.matches) {
      requestAnimationFrame(() =>
        panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    }
  }

  // Por defecto, la primera pregunta tal como se ve en la lista agrupada.
  const seleccion = visibles.find((t) => t.id === elegida) ?? grupos[0]?.preguntas[0]
  const textoLibre = visibles.filter((t) => t.tipo === 'texto_libre').length

  return (
    <div className="banco">
      <div className="encabezado">
        <div>
          <h1>Banco de preguntas</h1>
          <p className="texto-suave">
            Preguntas de todos los escenarios con su rúbrica de evaluación, por tipo de incidente,
            rol y dificultad.
          </p>
        </div>
      </div>

      <div className="banco-columnas">
        <section className="tarjeta banco-lista" aria-labelledby="titulo-banco">
          <div className="banco-lista-cabecera">
            <div>
              <h2 id="titulo-banco">
                Preguntas del banco <span className="contador">{visibles.length}</span>
              </h2>
              <p className="texto-suave">
                {textoLibre} de respuesta abierta · {visibles.length - textoLibre} de selección
              </p>
            </div>
            <label className="campo campo-agrupar">
              <span>Agrupar por</span>
              <select
                value={agrupacion}
                onChange={(e) => setAgrupacion(e.target.value as Agrupacion)}
              >
                {(Object.keys(ETIQUETA_AGRUPACION) as Agrupacion[]).map((a) => (
                  <option key={a} value={a}>
                    {ETIQUETA_AGRUPACION[a]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="filtros-biblioteca banco-filtros" role="group" aria-label="Filtros">
            <label className="campo campo-busqueda">
              <span>Buscar</span>
              <span className="campo-icono">
                <Search aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Pregunta o escenario…"
                  value={texto}
                  maxLength={100}
                  onChange={(e) => setTexto(e.target.value)}
                />
              </span>
            </label>
            <label className="campo">
              <span>Tipo de incidente</span>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                <option value="">Todos</option>
                {tipos.datos?.map((t) => (
                  <option key={t.codigo} value={t.codigo}>
                    {t.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span>Rol</span>
              <select value={rolFiltro} onChange={(e) => setRolFiltro(e.target.value)}>
                <option value="">Todos</option>
                {roles.datos?.map((r) => (
                  <option key={r.codigo} value={r.codigo}>
                    {r.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span>Dificultad</span>
              <select value={dificultad} onChange={(e) => setDificultad(e.target.value)}>
                <option value="">Todas</option>
                {NIVELES.map((n) => (
                  <option key={n} value={n}>
                    {ETIQUETA_NIVEL[n]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <Errores errores={banco.errores} />
          {banco.cargando && !banco.datos && <Cargando />}
          {banco.datos && visibles.length === 0 && (
            <div className="vacio">No hay preguntas con esos filtros.</div>
          )}

          {grupos.map((g) => (
            <section key={g.clave} className="banco-grupo" aria-label={g.titulo}>
              <h3 className="banco-grupo-titulo">
                {g.titulo}
                <span>
                  {g.detalle ? `${g.detalle} · ` : ''}
                  {g.preguntas.length} {g.preguntas.length === 1 ? 'pregunta' : 'preguntas'}
                </span>
              </h3>
              <div className="banco-grilla">
                {g.preguntas.map((t) => {
                  const activa = seleccion?.id === t.id
                  return (
                    <button
                      key={t.id}
                      type="button"
                      className={`pregunta-banco${activa ? ' activa' : ''}`}
                      aria-pressed={activa}
                      onClick={() => elegir(t.id)}
                    >
                      <span className="pregunta-banco-enunciado">{t.enunciado}</span>
                      <span className="pregunta-banco-etiquetas">
                        <span className="chip">{nombreRol(roles.datos, t.rol_codigo)}</span>
                        <NivelBadge nivel={t.dificultad} />
                        <span className={`badge tipo-pregunta tipo-${t.tipo}`}>
                          {t.tipo === 'texto_libre' ? 'Abierta' : 'Selección'}
                        </span>
                      </span>
                      <span className="pregunta-banco-meta">
                        <span>
                          <Target aria-hidden="true" />
                          {t.puntaje_maximo} pts
                        </span>
                        <span>
                          <Clock aria-hidden="true" />
                          {formatoTiempo(t.tiempo_limite_segundos)}
                        </span>
                        <span>
                          <ListChecks aria-hidden="true" />
                          {t.tipo === 'texto_libre'
                            ? `${t.criterios.length} criterios`
                            : `${t.opciones.length} opciones`}
                        </span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </section>
          ))}
        </section>

        {seleccion && (
          <aside ref={panelRef} className="tarjeta banco-detalle" aria-labelledby="titulo-rubrica">
            <h2 id="titulo-rubrica">Evaluación y rúbrica</h2>
            <p className="banco-detalle-enunciado">{seleccion.enunciado}</p>
            <dl className="banco-detalle-datos">
              <div>
                <dt>Escenario</dt>
                <dd>
                  <Link to={`/escenarios/${seleccion.escenario_id}`}>
                    {seleccion.escenario_nombre}
                  </Link>
                </dd>
              </div>
              <div>
                <dt>Rol</dt>
                <dd>{nombreRol(roles.datos, seleccion.rol_codigo)}</dd>
              </div>
              <div>
                <dt>Momento</dt>
                <dd>{seleccion.inject_orden ? `Inject ${seleccion.inject_orden}` : 'En orden'}</dd>
              </div>
              <div>
                <dt>Puntaje · tiempo</dt>
                <dd>
                  {seleccion.puntaje_maximo} pts · {formatoTiempo(seleccion.tiempo_limite_segundos)}
                </dd>
              </div>
            </dl>

            {seleccion.tipo === 'texto_libre' ? (
              <section className="banco-detalle-seccion">
                <h3>1. Criterios de evaluación</h3>
                <p className="texto-suave">
                  La respuesta suma puntaje por cada criterio que cubre (palabras clave).
                </p>
                <ul className="criterios-chips">
                  {seleccion.criterios.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </section>
            ) : (
              <section className="banco-detalle-seccion">
                <h3>1. Opciones de respuesta</h3>
                <ul className="opciones-rubrica">
                  {seleccion.opciones.map((o) => (
                    <li key={o.texto} className={o.correcta ? 'correcta' : undefined}>
                      {o.correcta ? (
                        <CheckCircle2 aria-hidden="true" />
                      ) : (
                        <Circle aria-hidden="true" />
                      )}
                      <span>{o.texto}</span>
                      {o.correcta && <span className="solo-lector"> (correcta)</span>}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {seleccion.respuesta_esperada && (
              <section className="banco-detalle-seccion">
                <h3>2. Respuesta esperada</h3>
                <p className="respuesta-esperada">{seleccion.respuesta_esperada}</p>
              </section>
            )}

            <section className="banco-detalle-seccion">
              <h3>{seleccion.respuesta_esperada ? '3' : '2'}. Vista previa del participante</h3>
              <div className="vista-previa-participante" aria-label="Vista previa (no editable)">
                <p className="vista-previa-rol">
                  <MessageSquareText aria-hidden="true" />
                  Tu tarea ({nombreRol(roles.datos, seleccion.rol_codigo)})
                </p>
                <p>{seleccion.enunciado}</p>
                {seleccion.tipo === 'texto_libre' ? (
                  <div className="vista-previa-campo" aria-hidden="true">
                    Escribe tu respuesta aquí…
                  </div>
                ) : (
                  <ul className="vista-previa-opciones" aria-hidden="true">
                    {seleccion.opciones.map((o) => (
                      <li key={o.texto}>
                        <Circle />
                        {o.texto}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>

            <div className="banco-detalle-acciones">
              {puedeGestionarEscenarios && (
                <Link
                  className="boton boton-primario boton-destacado"
                  to={`/escenarios/${seleccion.escenario_id}/editar`}
                >
                  <Pencil aria-hidden="true" />
                  Editar en el escenario
                </Link>
              )}
              <Link className="boton boton-secundario" to={`/escenarios/${seleccion.escenario_id}`}>
                <ExternalLink aria-hidden="true" />
                Ver escenario
              </Link>
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}
