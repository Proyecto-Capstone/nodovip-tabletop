// PC-24: vista de solo lectura de una sesión activa, para el Administrador
// (permiso sesiones:monitorear). Nunca muestra texto de respuestas, opciones
// elegidas ni criterios (PB-10): solo el acumulado, igual que el
// leaderboard. No hay comandos ni ajustes de puntaje aquí: eso sigue
// requiriendo sesiones:conducir y ser el dueño de la sesión.

import { Clock, MessageSquareText, Users, Zap } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import type { DetalleMonitoreo } from '../api/monitoreo'
import { useSesion } from '../auth/sesionContext'
import { SinPermiso } from '../components/Etiquetas'
import { EstadoVivo } from '../components/EstadoVivo'
import { Indicador } from '../components/Indicador'
import { formatoReloj } from '../lib/useEnVivo'
import { useDetalleMonitoreo, useTiempoTranscurrido } from '../lib/useMonitoreo'
import { AvancePorRol, ProgresoParticipantes } from './PanelAvance'

export function MonitoreoSesionPage() {
  const { id = '' } = useParams()
  const { puede } = useSesion()
  const permitido = puede('sesiones:monitorear')
  const { datos, conexion, error, recibidaEn } = useDetalleMonitoreo(permitido ? id : undefined)

  if (!permitido) return <SinPermiso />
  if (error && !datos) {
    return (
      <div className="alerta alerta-aviso">
        {error} <Link to="/monitoreo">Volver al monitoreo</Link>
      </div>
    )
  }
  if (!datos) return <p className="texto-suave">Cargando…</p>

  return <Panel datos={datos} conexion={conexion} recibidaEn={recibidaEn} />
}

function Panel({
  datos,
  conexion,
  recibidaEn,
}: {
  datos: DetalleMonitoreo
  conexion: ReturnType<typeof useDetalleMonitoreo>['conexion']
  recibidaEn: number
}) {
  const fila = datos.sesion
  const segundos = useTiempoTranscurrido(fila, recibidaEn)
  const conectados = new Set(datos.conectados_ids)

  return (
    <>
      <div className="alerta alerta-aviso">Modo lectura — no puedes controlar esta sesión.</div>

      <Link to="/monitoreo" className="volver">
        ← Monitoreo
      </Link>
      <div className="encabezado">
        <div>
          <h1>{fila.nombre}</h1>
          <p className="texto-suave">
            Moderador: {fila.moderador_nombre} · {fila.escenario_nombre}
          </p>
        </div>
        <div className="acciones-fila">
          {conexion === 'reconectando' && <span className="texto-suave">Reconectando…</span>}
          <Link className="boton boton-secundario" to={`/leaderboard/${fila.id}`}>
            Ver leaderboard
          </Link>
          <EstadoVivo estado="en_curso" pausada={fila.pausada} />
        </div>
      </div>

      <section className="indicadores" aria-label="Resumen de la sesión">
        <Indicador
          tono={fila.pausada ? 'naranja' : 'gris'}
          icono={<Clock />}
          etiqueta="Tiempo transcurrido"
          valor={formatoReloj(segundos)}
          detalle={fila.pausada ? 'En pausa: el tiempo se detiene' : undefined}
        />
        <Indicador
          tono="verde"
          icono={<Users />}
          etiqueta="Conectados"
          valor={`${fila.conectados}/${fila.invitados}`}
        />
        <Indicador
          tono="azul"
          icono={<Zap />}
          etiqueta="Inject actual"
          valor={`${fila.inject_actual}/${fila.total_injects}`}
        />
        <Indicador
          tono="naranja"
          icono={<MessageSquareText />}
          etiqueta="Respuestas recibidas"
          valor={`${fila.respuestas_recibidas}/${fila.respuestas_esperadas}`}
        />
      </section>

      <div className="disenador-columnas">
        <ProgresoParticipantes
          injectActual={fila.inject_actual}
          filas={datos.participantes.map((p) => ({
            usuarioId: p.usuario_id,
            nombre: p.nombre,
            rolNombre: p.rol_nombre,
            conectado: conectados.has(p.usuario_id),
            respondidas: p.respondidas,
            esperadas: p.respondidas + p.sin_responder,
          }))}
        />
        <AvancePorRol
          roles={datos.roles}
          participantes={datos.participantes.map((p) => ({
            usuario_id: p.usuario_id,
            rol_codigo: p.rol_codigo,
          }))}
          conectados={conectados}
        />
      </div>
    </>
  )
}
