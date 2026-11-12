// PB-04: biblioteca de escenarios con búsqueda, filtros e indicadores.

import {
  Archive,
  ArrowRight,
  Eye,
  Layers,
  ListChecks,
  PenLine,
  Pencil,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  rutas,
  type EscenarioResumen,
  type RolEjercicio,
  type TipoEscenario,
} from '../api/escenarios'
import { crearSesion } from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Anillo } from '../components/Anillo'
import { Indicador } from '../components/Indicador'
import { Cargando, Errores, EstadoBadge, NivelBadge, SinPermiso } from '../components/Etiquetas'
import { ETIQUETA_NIVEL, NIVELES, nombreRol, nombreTipo } from '../lib/etiquetas'
import { useDebounce, useGet } from '../lib/useGet'

export function BibliotecaPage() {
  const { rol, puede, puedeGestionarEscenarios, puedeLeerEscenarios } = useSesion()
  const navegar = useNavigate()
  const [texto, setTexto] = useState('')
  const [tipo, setTipo] = useState('')
  const [nivel, setNivel] = useState('')
  const [rolFiltro, setRolFiltro] = useState('')
  const [estado, setEstado] = useState('')
  const [creando, setCreando] = useState<string | null>(null)
  const [erroresAccion, setErroresAccion] = useState<string[]>()
  const q = useDebounce(texto.trim())

  const habilitado = puedeLeerEscenarios
  const puedeDisenar = puede('sesiones:disenar')
  const tipos = useGet<TipoEscenario[]>(habilitado ? rutas.tipos : null, rol)
  const roles = useGet<RolEjercicio[]>(habilitado ? rutas.roles : null, rol)
  const escenarios = useGet<EscenarioResumen[]>(
    habilitado
      ? rutas.escenarios({
          q,
          tipo,
          nivel,
          rol: rolFiltro,
          estado: puedeGestionarEscenarios ? estado : undefined,
        })
      : null,
    rol,
  )
  // Indicadores: siempre sobre toda la biblioteca, no sobre lo filtrado.
  const todos = useGet<EscenarioResumen[]>(habilitado ? rutas.escenarios({}) : null, rol)
  const archivados = useGet<EscenarioResumen[]>(
    habilitado && puedeGestionarEscenarios ? rutas.escenarios({ estado: 'archivado' }) : null,
    rol,
  )

  if (!habilitado) return <SinPermiso />

  const hayFiltros = Boolean(texto || tipo || nivel || rolFiltro || estado)
  const lista = todos.datos ?? []
  const publicados = lista.filter((e) => e.estado === 'publicado')
  const borradores = lista.filter((e) => e.estado === 'borrador')
  const tiposCubiertos = new Set(publicados.map((e) => e.tipo_codigo)).size
  const totalTipos = tipos.datos?.length ?? 0
  const cobertura = totalTipos ? Math.round((tiposCubiertos / totalTipos) * 100) : 0
  const cargandoIndicadores = !todos.datos

  const limpiar = () => {
    setTexto('')
    setTipo('')
    setNivel('')
    setRolFiltro('')
    setEstado('')
  }

  const disenar = async (escenario: EscenarioResumen) => {
    setErroresAccion(undefined)
    setCreando(escenario.id)
    try {
      const sesion = await crearSesion(escenario.id)
      navegar(`/sesiones/${sesion.id}/disenar?paso=2`)
    } catch (error) {
      setErroresAccion(
        error instanceof ApiError
          ? error.errores
          : ['No se pudo crear la sesión. Intenta de nuevo.'],
      )
      setCreando(null)
    }
  }

  return (
    <div className="biblioteca">
      <div className="encabezado">
        <div>
          <h1>Biblioteca de escenarios</h1>
          <p className="texto-suave">
            {puedeGestionarEscenarios
              ? 'Escenarios base de NODOVIP. Solo los publicados están disponibles para los moderadores.'
              : 'Escenarios publicados que puedes usar como base para diseñar un tabletop.'}
          </p>
        </div>
        {puedeGestionarEscenarios && (
          <Link className="boton boton-primario boton-destacado" to="/escenarios/nuevo">
            <Plus aria-hidden="true" />
            Nuevo escenario
          </Link>
        )}
      </div>

      <section
        className="indicadores"
        aria-label="Resumen de la biblioteca"
        aria-busy={cargandoIndicadores}
      >
        {puedeGestionarEscenarios ? (
          <>
            <Indicador
              tono="azul"
              icono={<Layers />}
              etiqueta="Escenarios activos"
              valor={cargandoIndicadores ? '—' : lista.length}
              detalle={
                archivados.datos ? `${archivados.datos.length} archivados aparte` : undefined
              }
            />
            <Indicador
              tono="verde"
              icono={<Send />}
              etiqueta="Publicados"
              valor={cargandoIndicadores ? '—' : publicados.length}
              detalle="Visibles para los moderadores"
            />
            <Indicador
              tono="naranja"
              icono={<PenLine />}
              etiqueta="En borrador"
              valor={cargandoIndicadores ? '—' : borradores.length}
              detalle="Pendientes de publicar"
            />
          </>
        ) : (
          <Indicador
            tono="verde"
            icono={<ShieldCheck />}
            etiqueta="Disponibles"
            valor={cargandoIndicadores ? '—' : publicados.length}
            detalle="Escenarios publicados"
          />
        )}
        <div className="indicador indicador-cobertura">
          <Anillo porcentaje={cobertura} />
          <div>
            <p className="indicador-etiqueta">Cobertura de incidentes</p>
            <p className="indicador-valor">
              {cargandoIndicadores ? '—' : `${tiposCubiertos} de ${totalTipos}`}
            </p>
            <p className="indicador-detalle">Tipos con un escenario publicado</p>
          </div>
        </div>
      </section>

      <section className="filtros-biblioteca" aria-label="Filtros">
        <label className="campo campo-busqueda">
          <span>Buscar</span>
          <span className="campo-icono">
            <Search aria-hidden="true" />
            <input
              type="search"
              placeholder="Nombre o descripción…"
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
          <span>Complejidad</span>
          <select value={nivel} onChange={(e) => setNivel(e.target.value)}>
            <option value="">Todas</option>
            {NIVELES.map((n) => (
              <option key={n} value={n}>
                {ETIQUETA_NIVEL[n]}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Rol involucrado</span>
          <select value={rolFiltro} onChange={(e) => setRolFiltro(e.target.value)}>
            <option value="">Todos</option>
            {roles.datos?.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.nombre}
              </option>
            ))}
          </select>
        </label>
        {puedeGestionarEscenarios && (
          <label className="campo">
            <span>Estado</span>
            <select value={estado} onChange={(e) => setEstado(e.target.value)}>
              <option value="">Borrador y publicados</option>
              <option value="borrador">Borrador</option>
              <option value="publicado">Publicado</option>
              <option value="archivado">Archivado</option>
            </select>
          </label>
        )}
      </section>

      <div className="resultado-biblioteca">
        <p className="texto-suave" aria-live="polite">
          {escenarios.datos
            ? `${escenarios.datos.length} ${escenarios.datos.length === 1 ? 'escenario' : 'escenarios'}${hayFiltros ? ' con los filtros aplicados' : ''}`
            : ''}
        </p>
        {hayFiltros && (
          <button type="button" className="boton boton-texto" onClick={limpiar}>
            Limpiar filtros
          </button>
        )}
      </div>

      <Errores errores={escenarios.errores ?? erroresAccion} />
      {escenarios.cargando && !escenarios.datos && <Cargando />}

      {escenarios.datos && escenarios.datos.length === 0 && (
        <div className="tarjeta vacio">
          {hayFiltros
            ? 'Ningún escenario coincide con los filtros.'
            : 'Todavía no hay escenarios en la biblioteca.'}
        </div>
      )}

      <div className="grilla-escenarios">
        {escenarios.datos?.map((e) => (
          <article key={e.id} className={`tarjeta-escenario nivel-borde-${e.nivel}`}>
            <div className="tarjeta-escenario-cabecera">
              <span className="tipo" title={nombreTipo(tipos.datos, e.tipo_codigo)}>
                {nombreTipo(tipos.datos, e.tipo_codigo)}
              </span>
              <NivelBadge nivel={e.nivel} />
              {puedeGestionarEscenarios && (
                <span className="empujar-derecha">
                  <EstadoBadge estado={e.estado} />
                </span>
              )}
            </div>
            <h2>
              <Link to={`/escenarios/${e.id}`} className="enlace-tarjeta">
                {e.nombre}
              </Link>
            </h2>
            <ul className="chips" aria-label="Roles involucrados">
              {e.roles.map((r) => (
                <li key={r} className="chip">
                  {nombreRol(roles.datos, r)}
                </li>
              ))}
            </ul>
            <p className="conteos">
              <span>
                <Zap aria-hidden="true" />
                {e.total_injects} injects
              </span>
              <span>
                <ListChecks aria-hidden="true" />
                {e.total_tareas} tareas
              </span>
            </p>
            <div className="tarjeta-escenario-acciones">
              {puedeDisenar && e.estado === 'publicado' ? (
                <>
                  <button
                    type="button"
                    className="boton boton-primario boton-destacado"
                    disabled={creando !== null}
                    onClick={() => disenar(e)}
                  >
                    {creando === e.id ? 'Creando…' : 'Diseñar tabletop'}
                    {creando !== e.id && <ArrowRight aria-hidden="true" />}
                  </button>
                  <Link className="boton boton-secundario" to={`/escenarios/${e.id}`}>
                    <Eye aria-hidden="true" />
                    Ver detalle
                  </Link>
                </>
              ) : (
                <>
                  <Link className="boton boton-primario boton-destacado" to={`/escenarios/${e.id}`}>
                    <Eye aria-hidden="true" />
                    Ver detalle
                  </Link>
                  {puedeGestionarEscenarios &&
                    (e.estado === 'archivado' ? (
                      <span className="boton boton-secundario boton-inactivo" aria-disabled="true">
                        <Archive aria-hidden="true" />
                        Archivado
                      </span>
                    ) : (
                      <Link
                        className="boton boton-secundario"
                        to={`/escenarios/${e.id}/editar`}
                        aria-label={`Editar ${e.nombre}`}
                      >
                        <Pencil aria-hidden="true" />
                        Editar
                      </Link>
                    ))}
                </>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
