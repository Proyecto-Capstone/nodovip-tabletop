// PB-04: biblioteca de escenarios con búsqueda y filtros.

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  rutas,
  type EscenarioResumen,
  type RolEjercicio,
  type TipoEscenario,
} from '../api/escenarios'
import { useSesion } from '../auth/sesionContext'
import {
  Cargando,
  Errores,
  EstadoBadge,
  NivelBadge,
  SinPermiso,
} from '../components/Etiquetas'
import { ETIQUETA_NIVEL, NIVELES, nombreRol, nombreTipo } from '../lib/etiquetas'
import { useDebounce, useGet } from '../lib/useGet'

export function BibliotecaPage() {
  const { rol, puedeGestionarEscenarios, puedeLeerEscenarios } = useSesion()
  const [texto, setTexto] = useState('')
  const [tipo, setTipo] = useState('')
  const [nivel, setNivel] = useState('')
  const [rolFiltro, setRolFiltro] = useState('')
  const [estado, setEstado] = useState('')
  const q = useDebounce(texto.trim())

  const habilitado = puedeLeerEscenarios
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

  if (!habilitado) return <SinPermiso />

  const hayFiltros = Boolean(texto || tipo || nivel || rolFiltro || estado)

  return (
    <>
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
          <Link className="boton boton-primario" to="/escenarios/nuevo">
            + Nuevo escenario
          </Link>
        )}
      </div>

      <section className="tarjeta filtros" aria-label="Filtros">
        <label className="campo campo-busqueda">
          <span>Buscar</span>
          <input
            type="search"
            placeholder="Nombre o descripción…"
            value={texto}
            maxLength={100}
            onChange={(e) => setTexto(e.target.value)}
          />
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
              <option value="">Borradores y publicados</option>
              <option value="borrador">Borrador</option>
              <option value="publicado">Publicado</option>
              <option value="archivado">Archivado</option>
            </select>
          </label>
        )}
        {hayFiltros && (
          <button
            type="button"
            className="boton boton-texto"
            onClick={() => {
              setTexto('')
              setTipo('')
              setNivel('')
              setRolFiltro('')
              setEstado('')
            }}
          >
            Limpiar filtros
          </button>
        )}
      </section>

      <Errores errores={escenarios.errores} />
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
          <Link key={e.id} to={`/escenarios/${e.id}`} className="tarjeta tarjeta-escenario">
            <div className="fila-badges">
              <span className="tipo">{nombreTipo(tipos.datos, e.tipo_codigo)}</span>
              <NivelBadge nivel={e.nivel} />
              {puedeGestionarEscenarios && <EstadoBadge estado={e.estado} />}
            </div>
            <h2>{e.nombre}</h2>
            <div className="chips">
              {e.roles.map((r) => (
                <span key={r} className="chip">
                  {nombreRol(roles.datos, r)}
                </span>
              ))}
            </div>
            <p className="conteos">
              {e.total_injects} injects · {e.total_tareas} tareas
            </p>
          </Link>
        ))}
      </div>
    </>
  )
}
