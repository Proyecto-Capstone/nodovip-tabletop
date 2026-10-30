// PC-24: panel de monitoreo de todas las sesiones activas, solo para el
// Administrador (permiso sesiones:monitorear). Se refresca cada 5 s
// mientras la pestaña está visible y deja entrar a cualquier sesión en
// modo de solo lectura.

import { Link } from 'react-router-dom'
import type { FilaMonitoreo } from '../api/monitoreo'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { EstadoVivo } from '../components/EstadoVivo'
import { formatoReloj } from '../lib/useEnVivo'
import { useResumenMonitoreo } from '../lib/useMonitoreo'

const formatoDuracion = (minutos: number) => {
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  return h > 0 ? `${h} h ${m} min` : `${m} min`
}

// Wall-clock, igual que excede_duracion en el backend: no descuenta pausas,
// porque lo que importa aquí es cuánto tiempo real lleva ocupando un cupo.
const minutosDesdeQueInicio = (iniciadaEn: string | null) => {
  if (!iniciadaEn) return 0
  return Math.max(0, Math.floor((Date.now() - new Date(iniciadaEn).getTime()) / 60000))
}

export function MonitoreoPage() {
  const { puede } = useSesion()
  const permitido = puede('sesiones:monitorear')
  const { datos, errores, cargando } = useResumenMonitoreo(permitido)

  if (!permitido) return <SinPermiso />

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Monitoreo de sesiones</h1>
          <p className="texto-suave">Sesiones en curso en este momento, en modo de solo lectura.</p>
        </div>
      </div>

      <Errores errores={errores} />
      {cargando && <Cargando />}
      {datos && <Cupo activas={datos.activas} maximo={datos.maximo} />}

      {datos?.sesiones.length === 0 && <p className="tarjeta vacio">No hay sesiones activas.</p>}

      <div className="lista-mis-sesiones">
        {datos?.sesiones.map((f) => (
          <TarjetaSesion key={f.id} fila={f} />
        ))}
      </div>
    </>
  )
}

function Cupo({ activas, maximo }: { activas: number; maximo: number }) {
  const lleno = maximo > 0 && activas >= maximo
  const porcentaje = maximo > 0 ? Math.min(100, (activas / maximo) * 100) : 0
  return (
    <div className="tarjeta">
      <p className="parrafo">
        <strong>
          {activas} de {maximo} sesiones activas
        </strong>
      </p>
      <div
        className={`barra-avance ${lleno ? 'cupo-lleno' : ''}`}
        role="progressbar"
        aria-label="Cupo de sesiones activas"
        aria-valuenow={activas}
        aria-valuemin={0}
        aria-valuemax={maximo}
      >
        <span style={{ width: `${porcentaje}%` }} />
      </div>
    </div>
  )
}

function TarjetaSesion({ fila }: { fila: FilaMonitoreo }) {
  return (
    <div className="tarjeta tarjeta-sesion">
      <div className="fila-badges">
        <EstadoVivo estado="en_curso" pausada={fila.pausada} />
        {fila.excede_duracion && (
          <span className="badge badge-ajustado">
            Excede la duración: {formatoDuracion(minutosDesdeQueInicio(fila.iniciada_en))} de{' '}
            {fila.duracion_minutos ?? '—'} min
          </span>
        )}
      </div>
      <h2>{fila.nombre}</h2>
      <p className="texto-suave">Moderador: {fila.moderador_nombre}</p>
      <p className="texto-suave">{fila.escenario_nombre}</p>

      <div className="metricas">
        <Metrica valor={formatoReloj(fila.segundos_transcurridos)} nombre="Tiempo transcurrido" />
        <Metrica valor={`${fila.conectados}/${fila.invitados}`} nombre="Conectados" />
        <Metrica valor={`${fila.inject_actual}/${fila.total_injects}`} nombre="Inject actual" />
      </div>

      <div
        className="barra-avance"
        role="progressbar"
        aria-label={`Avance de respuestas de ${fila.nombre}`}
        aria-valuenow={Math.round(fila.porcentaje_avance)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span style={{ width: `${fila.porcentaje_avance}%` }} />
      </div>
      <p className="texto-suave">
        {fila.respuestas_recibidas}/{fila.respuestas_esperadas} respuestas
      </p>

      <Link className="boton boton-texto" to={`/monitoreo/${fila.id}`}>
        Ver en modo lectura
      </Link>
    </div>
  )
}

function Metrica({ valor, nombre }: { valor: string; nombre: string }) {
  return (
    <div className="tarjeta metrica">
      <strong>{valor}</strong>
      <span className="texto-suave">{nombre}</span>
    </div>
  )
}
