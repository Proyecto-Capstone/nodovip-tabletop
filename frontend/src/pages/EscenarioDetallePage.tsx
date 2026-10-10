// PB-04: detalle del escenario. PB-03: acciones del Administrador.

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  archivarEscenario,
  publicarEscenario,
  rutas,
  type EscenarioDetalle,
  type RolEjercicio,
  type TipoEscenario,
} from '../api/escenarios'
import { useRol } from '../auth/rolContext'
import {
  Cargando,
  Errores,
  EstadoBadge,
  NivelBadge,
  SinPermiso,
} from '../components/Etiquetas'
import { formatoTiempo, nombreRol, nombreTipo } from '../lib/etiquetas'
import { useGet } from '../lib/useGet'

export function EscenarioDetallePage() {
  const { id = '' } = useParams()
  const { rol, esAdministrador, puedeLeerEscenarios } = useRol()
  const habilitado = puedeLeerEscenarios
  const escenario = useGet<EscenarioDetalle>(
    habilitado ? rutas.escenario(id) : null,
    rol,
  )
  const tipos = useGet<TipoEscenario[]>(habilitado ? rutas.tipos : null, rol)
  const roles = useGet<RolEjercicio[]>(habilitado ? rutas.roles : null, rol)
  const [erroresAccion, setErroresAccion] = useState<string[]>()
  const [enviando, setEnviando] = useState(false)

  if (!habilitado) return <SinPermiso />
  if (escenario.status === 404) {
    return (
      <div className="tarjeta vacio">
        Escenario no encontrado. <Link to="/escenarios">Volver a la biblioteca</Link>
      </div>
    )
  }
  if (!escenario.datos) {
    return escenario.errores ? <Errores errores={escenario.errores} /> : <Cargando />
  }

  const e = escenario.datos
  const pendientes = e.pendientes_para_publicar

  const ejecutar = async (accion: () => Promise<unknown>) => {
    setEnviando(true)
    setErroresAccion(undefined)
    try {
      await accion()
      escenario.recargar()
    } catch (error) {
      setErroresAccion(
        error instanceof ApiError ? error.errores : ['Error de conexión'],
      )
    } finally {
      setEnviando(false)
    }
  }

  const tareasPorRol = e.roles.map((codigo) => ({
    codigo,
    tareas: e.tareas.filter((t) => t.rol_codigo === codigo),
  }))

  return (
    <>
      <Link to="/escenarios" className="volver">
        ← Biblioteca de escenarios
      </Link>

      <div className="encabezado">
        <div>
          <div className="fila-badges">
            <span className="tipo">{nombreTipo(tipos.datos, e.tipo_codigo)}</span>
            <NivelBadge nivel={e.nivel} />
            <EstadoBadge estado={e.estado} />
          </div>
          <h1>{e.nombre}</h1>
        </div>
        <div className="acciones">
          {esAdministrador && e.estado !== 'archivado' && (
            <>
              <Link className="boton" to={`/escenarios/${e.id}/editar`}>
                Editar
              </Link>
              {e.estado === 'borrador' && (
                <button
                  type="button"
                  className="boton boton-primario"
                  disabled={enviando || pendientes.length > 0}
                  title={pendientes.length ? 'Completa los pendientes para publicar' : ''}
                  onClick={() => ejecutar(() => publicarEscenario(e.id))}
                >
                  Publicar
                </button>
              )}
              <button
                type="button"
                className="boton boton-peligro"
                disabled={enviando}
                onClick={() => {
                  if (
                    confirm(
                      'Archivar el escenario lo quita de la biblioteca. ¿Continuar?',
                    )
                  ) {
                    ejecutar(() => archivarEscenario(e.id))
                  }
                }}
              >
                Archivar
              </button>
            </>
          )}
          {!esAdministrador && (
            <button
              type="button"
              className="boton boton-primario"
              disabled
              title="Disponible con el diseñador de tabletop (PB-05)"
            >
              Usar como base
            </button>
          )}
        </div>
      </div>

      <Errores errores={erroresAccion} />

      {esAdministrador && e.estado === 'borrador' && pendientes.length > 0 && (
        <div className="alerta alerta-aviso">
          <strong>Pendiente para publicar:</strong>
          <ul>
            {pendientes.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="tarjeta">
        <h2>Descripción del incidente</h2>
        <p className="parrafo">{e.descripcion}</p>
        <h3>Roles involucrados</h3>
        <div className="chips">
          {e.roles.map((r) => (
            <span key={r} className="chip">
              {nombreRol(roles.datos, r)}
            </span>
          ))}
        </div>
      </section>

      <section className="tarjeta">
        <h2>Injects ({e.injects.length})</h2>
        <ol className="linea-tiempo">
          {e.injects.map((i) => (
            <li key={i.id}>
              <div className="inject-cabecera">
                <span className="inject-numero">Inject {i.orden}</span>
                {i.minuto_sugerido !== null && (
                  <span className="texto-suave">minuto {i.minuto_sugerido}</span>
                )}
              </div>
              <strong>{i.titulo}</strong>
              <p className="parrafo">{i.descripcion}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="tarjeta">
        <h2>Tareas por rol ({e.tareas.length})</h2>
        <div className="tareas-por-rol">
          {tareasPorRol.map((grupo) => (
            <div key={grupo.codigo} className="grupo-rol">
              <h3>
                {nombreRol(roles.datos, grupo.codigo)}{' '}
                <span className="texto-suave">({grupo.tareas.length})</span>
              </h3>
              {grupo.tareas.length === 0 && (
                <p className="texto-suave">Sin tareas asignadas.</p>
              )}
              {grupo.tareas.map((t) => (
                <article key={t.id} className="tarea">
                  <p className="tarea-enunciado">{t.enunciado}</p>
                  <div className="fila-badges">
                    <NivelBadge nivel={t.dificultad} />
                    <span className="texto-suave">
                      {t.puntaje_maximo} pts · {formatoTiempo(t.tiempo_limite_segundos)}
                    </span>
                  </div>
                  <details>
                    <summary>Criterios de evaluación ({t.criterios.length})</summary>
                    <ul>
                      {t.criterios.map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                    </ul>
                    {t.respuesta_esperada && (
                      <p className="parrafo">
                        <strong>Respuesta esperada:</strong> {t.respuesta_esperada}
                      </p>
                    )}
                  </details>
                </article>
              ))}
            </div>
          ))}
        </div>
      </section>
    </>
  )
}
