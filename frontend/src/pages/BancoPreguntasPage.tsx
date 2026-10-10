// RF-04 / PB-04: banco de preguntas reutilizable, por tipo, rol y dificultad.

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  rutas,
  type RolEjercicio,
  type TareaBanco,
  type TipoEscenario,
} from '../api/escenarios'
import { useRol } from '../auth/rolContext'
import { Cargando, Errores, NivelBadge, SinPermiso } from '../components/Etiquetas'
import {
  ETIQUETA_NIVEL,
  NIVELES,
  formatoTiempo,
  nombreRol,
  nombreTipo,
} from '../lib/etiquetas'
import { useGet } from '../lib/useGet'

export function BancoPreguntasPage() {
  const { rol, puedeLeerEscenarios } = useRol()
  const [tipo, setTipo] = useState('')
  const [rolFiltro, setRolFiltro] = useState('')
  const [dificultad, setDificultad] = useState('')

  const habilitado = puedeLeerEscenarios
  const tipos = useGet<TipoEscenario[]>(habilitado ? rutas.tipos : null, rol)
  const roles = useGet<RolEjercicio[]>(habilitado ? rutas.roles : null, rol)
  const banco = useGet<TareaBanco[]>(
    habilitado ? rutas.banco({ tipo, rol: rolFiltro, dificultad }) : null,
    rol,
  )

  if (!habilitado) return <SinPermiso />

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Banco de preguntas</h1>
          <p className="texto-suave">
            Preguntas y tareas de los escenarios, clasificadas por tipo de incidente,
            rol y dificultad.
          </p>
        </div>
      </div>

      <section className="tarjeta filtros" aria-label="Filtros">
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
      </section>

      <Errores errores={banco.errores} />
      {banco.cargando && !banco.datos && <Cargando />}
      {banco.datos?.length === 0 && (
        <div className="tarjeta vacio">No hay preguntas con esos filtros.</div>
      )}

      {banco.datos && banco.datos.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla">
            <thead>
              <tr>
                <th>Pregunta o tarea</th>
                <th>Rol</th>
                <th>Dificultad</th>
                <th>Puntaje / tiempo</th>
                <th>Escenario</th>
              </tr>
            </thead>
            <tbody>
              {banco.datos.map((t) => (
                <tr key={t.id}>
                  <td>
                    {t.enunciado}
                    <div className="texto-suave">
                      {t.criterios.length} criterio(s) de evaluación
                    </div>
                  </td>
                  <td>{nombreRol(roles.datos, t.rol_codigo)}</td>
                  <td>
                    <NivelBadge nivel={t.dificultad} />
                  </td>
                  <td className="sin-salto">
                    {t.puntaje_maximo} pts · {formatoTiempo(t.tiempo_limite_segundos)}
                  </td>
                  <td>
                    <Link to={`/escenarios/${t.escenario_id}`}>{t.escenario_nombre}</Link>
                    <div className="texto-suave">
                      {nombreTipo(tipos.datos, t.tipo_codigo)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
