// PC-24: panel de monitoreo de todas las sesiones activas, solo para el
// Administrador (permiso sesiones:monitorear). Se refresca cada 5 s
// mientras la pestaña está visible y deja entrar a cualquier sesión en
// modo de solo lectura.

import { Clock, Eye, MessageSquareText, PauseCircle, Radio, Users, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { FilaMonitoreo } from '../api/monitoreo'
import { useSesion } from '../auth/sesionContext'
import { Anillo } from '../components/Anillo'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { Indicador } from '../components/Indicador'
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

  const sesiones = datos?.sesiones ?? []
  const conectados = sesiones.reduce((s, f) => s + f.conectados, 0)
  const invitados = sesiones.reduce((s, f) => s + f.invitados, 0)
  const recibidas = sesiones.reduce((s, f) => s + f.respuestas_recibidas, 0)
  const esperadas = sesiones.reduce((s, f) => s + f.respuestas_esperadas, 0)
  const pausadas = sesiones.filter((f) => f.pausada).length

  return (
    <div className="monitoreo">
      <div className="encabezado">
        <div>
          <h1>Monitoreo de sesiones</h1>
          <p className="texto-suave">
            Sesiones en curso en este momento, en modo de solo lectura. Se actualiza cada 5
            segundos.
          </p>
        </div>
      </div>

      <Errores errores={errores} />
      {cargando && <Cargando />}
      {datos && (
        <section className="indicadores" aria-label="Resumen del monitoreo">
          <Cupo activas={datos.activas} maximo={datos.maximo} />
          <Indicador
            tono="verde"
            icono={<Users />}
            etiqueta="Participantes conectados"
            valor={conectados}
            detalle={`de ${invitados} invitados`}
          />
          <Indicador
            tono="azul"
            icono={<MessageSquareText />}
            etiqueta="Respuestas recibidas"
            valor={recibidas}
            detalle={`de ${esperadas} esperadas hasta ahora`}
          />
          <Indicador
            tono="naranja"
            icono={<PauseCircle />}
            etiqueta="Sesiones en pausa"
            valor={pausadas}
            detalle="El tiempo de las tareas se detiene"
          />
        </section>
      )}

      {datos?.sesiones.length === 0 && <p className="tarjeta vacio">
          No hay sesiones en curso. Cuando un moderador inicie una, aparecerá aquí en segundos.
        </p>}

      {sesiones.length > 0 && (
        <section className="leaderboard-grupo" aria-labelledby="titulo-activas">
          <h2 id="titulo-activas" className="leaderboard-grupo-titulo">
            <span className="punto-vivo" aria-hidden="true" />
            En curso ahora
          </h2>
          <div className="grilla-en-vivo">
            {sesiones.map((f) => (
              <TarjetaSesion key={f.id} fila={f} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function Cupo({ activas, maximo }: { activas: number; maximo: number }) {
  const lleno = maximo > 0 && activas >= maximo
  const porcentaje = maximo > 0 ? Math.min(100, (activas / maximo) * 100) : 0
  return (
    <div className={`indicador indicador-cupo ${lleno ? 'indicador-rojo' : ''}`}>
      <Anillo porcentaje={Math.round(porcentaje)} />
      <div className="indicador-cupo-texto">
        <p className="indicador-etiqueta">
          <Radio size={13} aria-hidden="true" /> Cupo de sesiones
        </p>
        <strong>
          {activas} de {maximo} sesiones activas
        </strong>
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
    </div>
  )
}

function TarjetaSesion({ fila }: { fila: FilaMonitoreo }) {
  return (
    <article
      className={`tarjeta-leaderboard tarjeta-monitoreo ${fila.pausada ? 'en-pausa' : 'en-vivo'}`}
      aria-labelledby={`sesion-${fila.id}`}
    >
      <div className="fila-badges">
        <EstadoVivo estado="en_curso" pausada={fila.pausada} />
        {fila.excede_duracion && (
          <span className="badge badge-ajustado">
            Excede la duración: {formatoDuracion(minutosDesdeQueInicio(fila.iniciada_en))} de{' '}
            {fila.duracion_minutos ?? '—'} min
          </span>
        )}
      </div>
      <h3 id={`sesion-${fila.id}`}>{fila.nombre}</h3>
      <div className="monitoreo-datos">
        <p className="texto-suave">Moderador: {fila.moderador_nombre}</p>
        <p className="monitoreo-escenario">{fila.escenario_nombre}</p>
      </div>

      <dl className="monitoreo-metricas">
        <div>
          <dt>
            <Clock aria-hidden="true" /> Tiempo
          </dt>
          <dd>{formatoReloj(fila.segundos_transcurridos)}</dd>
        </div>
        <div>
          <dt>
            <Users aria-hidden="true" /> Conectados
          </dt>
          <dd>{`${fila.conectados}/${fila.invitados}`}</dd>
        </div>
        <div>
          <dt>
            <Zap aria-hidden="true" /> Inject
          </dt>
          <dd>{`${fila.inject_actual}/${fila.total_injects}`}</dd>
        </div>
      </dl>

      <div className="monitoreo-avance">
        <span className="texto-suave">
          {fila.respuestas_recibidas}/{fila.respuestas_esperadas} respuestas
        </span>
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
      </div>

      <Link className="boton boton-secundario" to={`/monitoreo/${fila.id}`}>
        <Eye size={16} aria-hidden="true" />
        Ver en modo lectura
      </Link>
    </article>
  )
}
