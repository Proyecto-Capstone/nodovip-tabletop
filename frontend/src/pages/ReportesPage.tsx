// PB-14: sesiones finalizadas con su reporte de brechas (Analista, Moderador y
// Administrador). El Moderador solo ve las suyas.

import { Link } from 'react-router-dom'
import { rutasReportes, type EstadoReporte, type SesionConReporte } from '../api/reportes'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'

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

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Reportes de brechas</h1>
          <p className="texto-suave">
            Un reporte por cada sesión finalizada: puntajes, brechas por rol, trazabilidad de
            respuestas y recomendaciones.
          </p>
        </div>
      </div>

      <Errores errores={sesiones.errores} />
      {sesiones.cargando && <Cargando />}

      {sesiones.datos && sesiones.datos.length === 0 && (
        <div className="tarjeta vacio">Todavía no hay sesiones finalizadas.</div>
      )}

      {sesiones.datos && sesiones.datos.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla">
            <thead>
              <tr>
                <th>Sesión</th>
                <th>Cliente</th>
                <th>Finalizada</th>
                <th>Participantes</th>
                <th>PDF</th>
                <th>
                  <span className="solo-lector">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sesiones.datos.map((s) => (
                <tr key={s.id}>
                  <td>{s.nombre}</td>
                  <td>{s.cliente ?? <span className="texto-suave">Sin cliente</span>}</td>
                  <td className="sin-salto">{formatoFecha(s.finalizada_en)}</td>
                  <td>{s.participantes}</td>
                  <td>
                    <EstadoPdfBadge reporte={s.reporte} />
                  </td>
                  <td>
                    <Link className="boton boton-primario" to={`/reportes/${s.id}`}>
                      Ver reporte
                    </Link>
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
