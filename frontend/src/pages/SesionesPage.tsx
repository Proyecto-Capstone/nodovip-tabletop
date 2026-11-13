// PB-05: sesiones tabletop del moderador (borradores y programadas).
// PC-49: indicadores por estado, filtro rápido y búsqueda por nombre.

import { useState } from 'react'
import { CalendarClock, CheckCircle2, PencilLine, Radio, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  eliminarSesion,
  rutasSesiones,
  type EstadoSesion,
  type SesionResumen,
} from '../api/sesiones'
import { Indicador } from '../components/Indicador'
import { useSesion } from '../auth/sesionContext'
import { useConfirmar } from '../components/confirmacionContext'
import { Cargando, Errores, EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'
import { formatoDuracion, formatoFecha } from './disenador/comun'

const ORDEN_ESTADO: Record<EstadoSesion, number> = {
  en_curso: 0,
  programada: 1,
  borrador: 2,
  finalizada: 3,
}

const FILTROS: { valor: EstadoSesion | 'todas'; texto: string }[] = [
  { valor: 'todas', texto: 'Todas' },
  { valor: 'en_curso', texto: 'En curso' },
  { valor: 'programada', texto: 'Programadas' },
  { valor: 'borrador', texto: 'Borradores' },
  { valor: 'finalizada', texto: 'Finalizadas' },
]

export function SesionesPage() {
  const { rol, puede } = useSesion()
  const confirmar = useConfirmar()
  const permitido = puede('sesiones:disenar')
  const sesiones = useGet<SesionResumen[]>(permitido ? rutasSesiones.lista : null, rol)
  const [errores, setErrores] = useState<string[]>()
  const [filtro, setFiltro] = useState<EstadoSesion | 'todas'>('todas')
  const [busqueda, setBusqueda] = useState('')

  if (!permitido) return <SinPermiso />

  // PC-49: primero lo que requiere atención (en curso, programadas, borradores).
  const lista = [...(sesiones.datos ?? [])].sort(
    (a, b) => ORDEN_ESTADO[a.estado] - ORDEN_ESTADO[b.estado],
  )
  const cuenta = (estado: EstadoSesion) => lista.filter((s) => s.estado === estado).length
  const texto = busqueda.trim().toLowerCase()
  const visibles = lista.filter(
    (s) =>
      (filtro === 'todas' || s.estado === filtro) &&
      (!texto || s.nombre.toLowerCase().includes(texto)),
  )

  const eliminar = async (s: SesionResumen) => {
    const confirmado = await confirmar({
      titulo: `¿Eliminar el borrador "${s.nombre}"?`,
      textoConfirmar: 'Eliminar',
    })
    if (!confirmado) return
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
      {lista.length > 0 && (
        <section className="indicadores" aria-label="Resumen de mis tabletops">
          <Indicador
            tono="rojo"
            icono={<Radio />}
            etiqueta="En curso"
            valor={cuenta('en_curso')}
            detalle="Sesiones que estás conduciendo"
          />
          <Indicador
            tono="azul"
            icono={<CalendarClock />}
            etiqueta="Programadas"
            valor={cuenta('programada')}
            detalle="Listas para iniciar"
          />
          <Indicador
            tono="naranja"
            icono={<PencilLine />}
            etiqueta="Borradores"
            valor={cuenta('borrador')}
            detalle="Diseño sin terminar"
          />
          <Indicador
            tono="verde"
            icono={<CheckCircle2 />}
            etiqueta="Finalizadas"
            valor={cuenta('finalizada')}
            detalle="Con respuestas, reporte y debrief"
          />
        </section>
      )}

      {lista.length > 0 && (
        <div className="barra-herramientas">
          <div className="segmentos" role="group" aria-label="Filtrar por estado">
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
                  {f.valor === 'todas' ? lista.length : cuenta(f.valor)}
                </span>
              </button>
            ))}
          </div>
          <label className="campo campo-busqueda-compacta">
            <span className="solo-lector">Buscar sesión</span>
            <span className="campo-icono">
              <Search aria-hidden="true" />
              <input
                type="search"
                placeholder="Buscar por nombre"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
              />
            </span>
          </label>
        </div>
      )}

      {lista.length > 0 && visibles.length === 0 && (
        <p className="tarjeta vacio">Ninguna sesión coincide con el filtro.</p>
      )}

      {visibles.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla tabla-sesiones">
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
              {visibles.map((s) => (
                <tr key={s.id}>
                  <td>{s.nombre}</td>
                  <td>
                    <EstadoSesionBadge estado={s.estado} />
                  </td>
                  <td className="sin-salto">
                    {formatoFecha(s.fecha_programada)}
                    {s.duracion_minutos ? (
                      <span className="celda-secundaria">
                        {formatoDuracion(s.duracion_minutos)}
                      </span>
                    ) : null}
                  </td>
                  <td>
                    {s.total_participantes} / {s.roles.length} roles
                  </td>
                  <td>{s.puntaje_maximo_total}</td>
                  <td>
                    <div className="acciones-fila">
                      {(s.estado === 'programada' || s.estado === 'en_curso') && (
                        <Link className="boton boton-primario" to={`/sesiones/${s.id}/conducir`}>
                          {s.estado === 'en_curso' ? 'Volver a la sesión' : 'Conducir'}
                        </Link>
                      )}
                      {(s.estado === 'en_curso' || s.estado === 'finalizada') && (
                        <Link className="boton boton-texto" to={`/sesiones/${s.id}/respuestas`}>
                          Respuestas
                        </Link>
                      )}
                      {s.estado === 'finalizada' && puede('reportes:ver') && (
                        <Link className="boton boton-texto" to={`/reportes/${s.id}`}>
                          Reporte
                        </Link>
                      )}
                      {s.estado === 'finalizada' && puede('reportes:ver') && (
                        <Link className="boton boton-texto" to={`/sesiones/${s.id}/debrief`}>
                          Debrief
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
