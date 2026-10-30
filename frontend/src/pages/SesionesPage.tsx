// PB-05: sesiones tabletop del moderador (borradores y programadas).

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { eliminarSesion, rutasSesiones, type SesionResumen } from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'
import { formatoDuracion, formatoFecha } from './disenador/comun'

export function SesionesPage() {
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:disenar')
  const sesiones = useGet<SesionResumen[]>(permitido ? rutasSesiones.lista : null, rol)
  const [errores, setErrores] = useState<string[]>()

  if (!permitido) return <SinPermiso />

  const eliminar = async (s: SesionResumen) => {
    if (!confirm(`¿Eliminar el borrador "${s.nombre}"?`)) return
    setErrores(undefined)
    try {
      await eliminarSesion(s.id)
      sesiones.recargar()
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
    }
  }

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Mis tabletops</h1>
          <p className="texto-suave">
            Sesiones que diseñaste. Un borrador se puede retomar en cualquier momento.
          </p>
        </div>
        <Link className="boton boton-primario" to="/sesiones/nueva">
          + Diseñar tabletop
        </Link>
      </div>

      <Errores errores={errores ?? sesiones.errores} />
      {sesiones.cargando && <Cargando />}
      {sesiones.datos?.length === 0 && (
        <p className="tarjeta vacio">
          Todavía no diseñaste ninguna sesión. Empieza eligiendo un escenario.
        </p>
      )}
      {sesiones.datos && sesiones.datos.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla">
            <thead>
              <tr>
                <th>Sesión</th>
                <th>Estado</th>
                <th>Fecha</th>
                <th>Participantes</th>
                <th>Puntaje máx.</th>
                <th>
                  <span className="solo-lector">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sesiones.datos.map((s) => (
                <tr key={s.id}>
                  <td>{s.nombre}</td>
                  <td>
                    <EstadoSesionBadge estado={s.estado} />
                  </td>
                  <td className="sin-salto">
                    {formatoFecha(s.fecha_programada)}
                    {s.duracion_minutos ? ` · ${formatoDuracion(s.duracion_minutos)}` : ''}
                  </td>
                  <td>
                    {s.total_participantes} / {s.roles.length} roles
                  </td>
                  <td>{s.puntaje_maximo_total}</td>
                  <td>
                    <div className="acciones-fila">
                      {(s.estado === 'programada' || s.estado === 'en_curso') && (
                        <Link
                          className="boton boton-primario"
                          to={`/sesiones/${s.id}/conducir`}
                        >
                          {s.estado === 'en_curso' ? 'Volver a la sesión' : 'Conducir'}
                        </Link>
                      )}
                      {(s.estado === 'en_curso' || s.estado === 'finalizada') && (
                        <Link className="boton boton-texto" to={`/sesiones/${s.id}/respuestas`}>
                          Respuestas
                        </Link>
                      )}
                      <Link className="boton boton-texto" to={`/sesiones/${s.id}/disenar`}>
                        {s.estado === 'borrador' ? 'Continuar diseño' : 'Ver diseño'}
                      </Link>
                      {s.estado === 'borrador' && (
                        <button
                          type="button"
                          className="boton boton-texto texto-peligro"
                          onClick={() => eliminar(s)}
                        >
                          Eliminar
                        </button>
                      )}
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
