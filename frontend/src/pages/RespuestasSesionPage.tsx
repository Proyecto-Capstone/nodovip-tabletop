// PB-09: registro trazable de las respuestas de una sesión, para el moderador.
// Solo lectura: las respuestas registradas no se pueden modificar ni borrar.

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { rutaRespuestas, type RespuestaRegistrada } from '../api/respuestas'
import { rutasSesiones, type SesionDetalle } from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'

const formatoHora = (iso: string) =>
  new Date(iso).toLocaleString('es-EC', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

const formatoSegundos = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

export function RespuestasSesionPage() {
  const { id = '' } = useParams()
  const { rol } = useSesion()
  const sesion = useGet<SesionDetalle>(rutasSesiones.sesion(id), rol)
  const respuestas = useGet<RespuestaRegistrada[]>(rutaRespuestas(id), rol)
  const [rolFiltro, setRolFiltro] = useState('')
  const [injectFiltro, setInjectFiltro] = useState('')

  if (sesion.status === 404 || respuestas.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        Sesión no encontrada. <Link to="/sesiones">Volver a mis tabletops</Link>
      </div>
    )
  }

  const todas = respuestas.datos ?? []
  const roles = [...new Map(todas.map((r) => [r.rol_codigo, r.rol_nombre])).entries()]
  const injects = [...new Map(todas.map((r) => [r.inject_orden, r.inject_titulo])).entries()].sort(
    ([a], [b]) => a - b,
  )
  const visibles = todas.filter(
    (r) =>
      (!rolFiltro || r.rol_codigo === rolFiltro) &&
      (!injectFiltro || String(r.inject_orden) === injectFiltro),
  )

  return (
    <>
      <Link to="/sesiones" className="volver">
        ← Mis tabletops
      </Link>
      <div className="encabezado">
        <div>
          <h1>Registro de respuestas</h1>
          <p className="texto-suave">
            {sesion.datos?.nombre ?? '…'} · {todas.length}{' '}
            {todas.length === 1 ? 'respuesta' : 'respuestas'}, en orden de llegada con la hora del
            servidor.
          </p>
        </div>
        <div className="acciones-fila">
          {sesion.datos?.estado === 'en_curso' && (
            <Link className="boton boton-texto" to={`/sesiones/${id}/conducir`}>
              Volver al panel
            </Link>
          )}
          <button type="button" className="boton boton-texto" onClick={respuestas.recargar}>
            Actualizar
          </button>
        </div>
      </div>

      <p className="texto-suave nota-solo-lectura">
        🔒 Solo lectura: una respuesta registrada no se puede modificar ni borrar.
      </p>

      {todas.length > 0 && (
        <div className="tarjeta filtros">
          <label className="campo">
            Rol
            <select value={rolFiltro} onChange={(e) => setRolFiltro(e.target.value)}>
              <option value="">Todos</option>
              {roles.map(([codigo, nombre]) => (
                <option key={codigo} value={codigo}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            Inject
            <select value={injectFiltro} onChange={(e) => setInjectFiltro(e.target.value)}>
              <option value="">Todos</option>
              {injects.map(([orden, titulo]) => (
                <option key={orden} value={orden}>
                  {orden}. {titulo}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <Errores errores={respuestas.errores ?? sesion.errores} />
      {respuestas.cargando && !respuestas.datos && <Cargando />}

      {respuestas.datos && visibles.length === 0 && (
        <div className="tarjeta vacio">
          {todas.length === 0
            ? 'Todavía no hay respuestas registradas en esta sesión.'
            : 'No hay respuestas con esos filtros.'}
        </div>
      )}

      {visibles.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla tabla-respuestas">
            <thead>
              <tr>
                <th>Recibida</th>
                <th>Participante</th>
                <th>Rol</th>
                <th>Inject</th>
                <th>Tarea</th>
                <th>Respuesta</th>
                <th>Tiempo usado</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((r) => (
                <tr key={r.id}>
                  <td className="sin-salto">{formatoHora(r.recibida_en)}</td>
                  <td>
                    {r.participante_nombre}
                    <div className="texto-suave">{r.participante_correo}</div>
                  </td>
                  <td>{r.rol_nombre}</td>
                  <td className="sin-salto">
                    {r.inject_orden}. {r.inject_titulo}
                  </td>
                  <td>{r.tarea_enunciado}</td>
                  <td className="respuesta-registrada">
                    {r.tipo === 'texto_libre' ? (
                      r.texto
                    ) : (
                      <ul>
                        {r.opciones_elegidas_texto.map((o) => (
                          <li key={o}>{o}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td className="sin-salto">
                    {formatoSegundos(r.segundos_usados)} /{' '}
                    {formatoSegundos(r.tiempo_limite_segundos)}
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
