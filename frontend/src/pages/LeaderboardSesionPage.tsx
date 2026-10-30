// PB-12: leaderboard en vivo de una sesión, solo lectura (Observador,
// Administrador o el Moderador dueño). Nunca muestra texto de respuestas,
// opciones elegidas ni criterios: solo el acumulado (PB-10). Sigue el
// prototipo P-06 (Figura 21): tablero oscuro, podio y ranking completo.

import { Link, useParams } from 'react-router-dom'
import type { Leaderboard, PosicionParticipante, PosicionRol } from '../api/leaderboard'
import { useSesion } from '../auth/sesionContext'
import { EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useLeaderboard, useSegundosDesde } from '../lib/useLeaderboard'

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

const MEDALLA: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }

// Con 0 puntos no hay mérito que premiar: ni medalla ni fondo de podio,
// aunque la posición (por el empate) sea 1, 2 o 3.
const esPodio = (posicion: number, puntaje: number) => posicion <= 3 && puntaje > 0

const tierDeColor = (porcentaje: number) => {
  if (porcentaje >= 70) return 'tier-verde'
  if (porcentaje >= 40) return 'tier-naranja'
  return 'tier-rojo'
}

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

      <div className="tablero-leaderboard">
        <div className="tablero-leaderboard-principal">
          <RankingRoles roles={datos.roles} />
          <Podio participantes={datos.participantes} />
        </div>
        <RankingCompleto participantes={datos.participantes} />
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

function RankingRoles({ roles }: { roles: PosicionRol[] }) {
  return (
    <section className="tablero-seccion" aria-labelledby="titulo-ranking-roles">
      <h2 id="titulo-ranking-roles">Ranking por rol organizacional</h2>
      {roles.length === 0 ? (
        <p className="tablero-texto-suave">Sin roles en la sesión.</p>
      ) : (
        <ul className="ranking-roles-tablero">
          {roles.map((r) => (
            <li key={r.rol_codigo}>
              <span className="ranking-roles-nombre">
                <strong>{r.rol_nombre}</strong>
                <span className="tablero-texto-suave">
                  {r.participantes} {r.participantes === 1 ? 'participante' : 'participantes'}
                </span>
              </span>
              <div
                className={`barra-avance-tablero ${tierDeColor(r.porcentaje)}`}
                role="progressbar"
                aria-label={`Puntaje de ${r.rol_nombre}`}
                aria-valuenow={Math.round(r.porcentaje)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${r.porcentaje}%` }} />
              </div>
              <span className="ranking-roles-puntaje">
                {formatoPuntaje(r.puntaje)} / {r.maximo} pts
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Podio({ participantes }: { participantes: PosicionParticipante[] }) {
  const vistos = new Set<number>()
  const top3 = participantes
    .filter((p) => esPodio(p.posicion, p.puntaje))
    .filter((p) => (vistos.has(p.posicion) ? false : vistos.add(p.posicion)))
    .slice(0, 3)

  if (top3.length === 0) return null

  return (
    <div className="podio" role="group" aria-label="Podio">
      {top3.map((p) => (
        <div key={p.usuario_id} className={`podio-bloque podio-${p.posicion}`}>
          <span className="podio-puesto" aria-hidden="true">
            {MEDALLA[p.posicion]}
          </span>
          <strong className="podio-nombre">{p.nombre}</strong>
          <span className="podio-rol">{p.rol_nombre}</span>
          <span className="podio-puntos">{formatoPuntaje(p.puntaje)} pts</span>
        </div>
      ))}
    </div>
  )
}

function RankingCompleto({ participantes }: { participantes: PosicionParticipante[] }) {
  return (
    <section className="ranking-completo" aria-labelledby="titulo-ranking-completo">
      <h2 id="titulo-ranking-completo">Ranking completo</h2>
      {participantes.length === 0 ? (
        <p className="tablero-texto-suave">Todavía no hay participantes en esta sesión.</p>
      ) : (
        <ol>
          {participantes.map((p) => (
            <li
              key={p.usuario_id}
              className={esPodio(p.posicion, p.puntaje) ? 'leaderboard-podio' : undefined}
            >
              <span className="ranking-completo-puesto" aria-label={`Posición ${p.posicion}`}>
                {p.posicion}
              </span>
              <span className="ranking-completo-nombre">
                <strong>{p.nombre}</strong>
                <span className="tablero-texto-suave">{p.rol_nombre}</span>
              </span>
              <span className="ranking-completo-puntos">{formatoPuntaje(p.puntaje)} pts</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
