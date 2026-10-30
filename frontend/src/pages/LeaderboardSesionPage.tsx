// PB-12: leaderboard en vivo de una sesión, solo lectura (Observador,
// Administrador o el Moderador dueño). Nunca muestra texto de respuestas,
// opciones elegidas ni criterios: solo el acumulado (PB-10).

import { Link, useParams } from 'react-router-dom'
import type { Leaderboard, PosicionParticipante, PosicionRol } from '../api/leaderboard'
import { useSesion } from '../auth/sesionContext'
import { EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useLeaderboard, useSegundosDesde } from '../lib/useLeaderboard'

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

const MEDALLA: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }

export function LeaderboardSesionPage() {
  const { id = '' } = useParams()
  const { puede } = useSesion()
  const permitido = puede('leaderboard:ver')
  const { datos, conexion, error, recibidaEn } = useLeaderboard(permitido ? id : undefined)

  if (!permitido) return <SinPermiso />
  if (error && !datos) {
    return (
      <div className="alerta alerta-aviso">
        {error} <Link to="/leaderboard">Volver al leaderboard</Link>
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
  datos: Leaderboard
  conexion: ReturnType<typeof useLeaderboard>['conexion']
  recibidaEn: number
}) {
  const segundos = useSegundosDesde(recibidaEn)
  const finalizada = datos.sesion.estado === 'finalizada'

  return (
    <>
      <Link to="/leaderboard" className="volver">
        ← Leaderboard
      </Link>
      <div className="encabezado">
        <div>
          <h1>{datos.sesion.nombre}</h1>
          <p className="texto-suave">
            Inject {datos.sesion.inject_actual}/{datos.sesion.total_injects}
          </p>
        </div>
        <div className="acciones-fila">
          <IndicadorConexion
            conexion={conexion}
            finalizada={finalizada}
            segundos={segundos}
          />
          <EstadoSesionBadge estado={datos.sesion.estado} />
        </div>
      </div>

      {finalizada && (
        <p className="alerta alerta-aviso leaderboard-resultado-final">Resultado final</p>
      )}

      <div className="disenador-columnas">
        <RankingParticipantes participantes={datos.participantes} />
        <RankingRoles roles={datos.roles} />
      </div>
    </>
  )
}

function IndicadorConexion({
  conexion,
  finalizada,
  segundos,
}: {
  conexion: ReturnType<typeof useLeaderboard>['conexion']
  finalizada: boolean
  segundos: number
}) {
  if (finalizada) return null
  if (conexion === 'conectado') {
    return (
      <span className="texto-suave">
        <span className="badge badge-live">● EN VIVO</span> · Actualizado hace {segundos} s
      </span>
    )
  }
  if (conexion === 'reconectando') {
    return <span className="texto-suave">Reconectando…</span>
  }
  return null
}

function RankingParticipantes({ participantes }: { participantes: PosicionParticipante[] }) {
  return (
    <section className="tarjeta" aria-labelledby="titulo-ranking-participantes">
      <h2 id="titulo-ranking-participantes">Ranking por participante</h2>
      {participantes.length === 0 ? (
        <p className="texto-suave">Todavía no hay participantes en esta sesión.</p>
      ) : (
        <ul className="lista-leaderboard">
          {participantes.map((p) => (
            <li
              key={p.usuario_id}
              className={p.posicion <= 3 ? 'leaderboard-fila leaderboard-podio' : 'leaderboard-fila'}
            >
              <span className="leaderboard-posicion" aria-label={`Posición ${p.posicion}`}>
                {MEDALLA[p.posicion] ?? `#${p.posicion}`}
              </span>
              <span className="progreso-persona">
                <strong>{p.nombre}</strong>
                <span className="texto-suave">{p.rol_nombre}</span>
              </span>
              <div
                className="barra-avance"
                role="progressbar"
                aria-label={`Puntaje de ${p.nombre}`}
                aria-valuenow={Math.round(p.porcentaje)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${p.porcentaje}%` }} />
              </div>
              <span className="texto-suave leaderboard-puntaje">
                {formatoPuntaje(p.puntaje)} / {p.maximo} pts
              </span>
              <span className="texto-suave leaderboard-respuestas">
                {p.respondidas} resp. · {p.sin_responder} pend.
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function RankingRoles({ roles }: { roles: PosicionRol[] }) {
  return (
    <section className="tarjeta" aria-labelledby="titulo-ranking-roles">
      <h2 id="titulo-ranking-roles">Ranking por rol</h2>
      {roles.length === 0 ? (
        <p className="texto-suave">Sin roles en la sesión.</p>
      ) : (
        <ul className="lista-leaderboard">
          {roles.map((r) => (
            <li
              key={r.rol_codigo}
              className={r.posicion <= 3 ? 'leaderboard-fila leaderboard-podio' : 'leaderboard-fila'}
            >
              <span className="leaderboard-posicion" aria-label={`Posición ${r.posicion}`}>
                {MEDALLA[r.posicion] ?? `#${r.posicion}`}
              </span>
              <span className="progreso-persona">
                <strong>{r.rol_nombre}</strong>
                <span className="texto-suave">{r.participantes} participantes</span>
              </span>
              <div
                className="barra-avance"
                role="progressbar"
                aria-label={`Puntaje de ${r.rol_nombre}`}
                aria-valuenow={Math.round(r.porcentaje)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${r.porcentaje}%` }} />
              </div>
              <span className="texto-suave leaderboard-puntaje">
                {formatoPuntaje(r.puntaje)} / {r.maximo} pts
              </span>
              <span className="texto-suave leaderboard-respuestas">
                {r.respondidas} resp. · {r.sin_responder} pend.
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
