// PB-12: leaderboard en vivo de una sesión, solo lectura (Observador,
// Administrador o el Moderador dueño). Nunca muestra texto de respuestas,
// opciones elegidas ni criterios: solo el acumulado (PB-10). Sigue el
// prototipo P-06 (Figura 21): tablero oscuro, podio y ranking completo.

import { ArrowLeft, Circle, Crown, Medal, Percent, Trophy, Users, Zap } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import type { Leaderboard, PosicionParticipante, PosicionRol } from '../api/leaderboard'
import { useSesion } from '../auth/sesionContext'
import { EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useLeaderboard, useSegundosDesde } from '../lib/useLeaderboard'

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

// Con 0 puntos no hay mérito que premiar: ni medalla ni fondo de podio,
// aunque la posición (por el empate) sea 1, 2 o 3.
const esPodio = (posicion: number, puntaje: number) => posicion <= 3 && puntaje > 0

const tierDeColor = (porcentaje: number) => {
  if (porcentaje >= 70) return 'tier-verde'
  if (porcentaje >= 40) return 'tier-naranja'
  return 'tier-rojo'
}

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean)
  return (
    (partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')
  ).toUpperCase()
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
  const { sesion, participantes } = datos
  const finalizada = sesion.estado === 'finalizada'
  const avanceInjects = sesion.total_injects
    ? Math.round((sesion.inject_actual / sesion.total_injects) * 100)
    : 0
  const promedio = participantes.length
    ? Math.round(participantes.reduce((suma, p) => suma + p.porcentaje, 0) / participantes.length)
    : 0
  const respondidas = participantes.reduce((suma, p) => suma + p.respondidas, 0)
  const pendientes = participantes.reduce((suma, p) => suma + p.sin_responder, 0)
  const lider = participantes.find((p) => esPodio(p.posicion, p.puntaje))

  return (
    <div className="leaderboard-sesion">
      <Link to="/leaderboard" className="volver">
        <ArrowLeft size={16} aria-hidden="true" />
        Leaderboard
      </Link>

      <section className="leaderboard-hero" aria-label="Resumen de la sesión">
        <div className="leaderboard-hero-principal">
          <div className="fila-badges">
            <EstadoSesionBadge estado={sesion.estado} />
            <IndicadorConexion conexion={conexion} finalizada={finalizada} segundos={segundos} />
          </div>
          <h1>{sesion.nombre}</h1>
          <div className="avance-injects avance-injects-grande">
            <span className="texto-suave">
              Inject {sesion.inject_actual}/{sesion.total_injects}
            </span>
            <span className="avance-injects-barra" aria-hidden="true">
              <span style={{ width: `${avanceInjects}%` }} />
            </span>
          </div>
        </div>
        <dl className="leaderboard-hero-cifras">
          <div>
            <dt>
              <Users aria-hidden="true" /> Participantes
            </dt>
            <dd>{participantes.length}</dd>
          </div>
          <div>
            <dt>
              <Percent aria-hidden="true" /> Promedio
            </dt>
            <dd>{promedio}%</dd>
          </div>
          <div>
            <dt>
              <Zap aria-hidden="true" /> Respuestas
            </dt>
            <dd>
              {respondidas}
              <small>/{respondidas + pendientes}</small>
            </dd>
          </div>
          <div>
            <dt>
              <Crown aria-hidden="true" /> Líder
            </dt>
            <dd className="leaderboard-hero-lider">{lider ? lider.nombre : '—'}</dd>
          </div>
        </dl>
      </section>

      {finalizada && (
        <p className="alerta leaderboard-resultado-final">
          <Trophy size={18} aria-hidden="true" />
          Resultado final
        </p>
      )}

      <div className="tablero-leaderboard">
        <div className="tablero-leaderboard-principal">
          <Podio participantes={participantes} />
          <RankingRoles roles={datos.roles} />
        </div>
        <RankingCompleto participantes={participantes} />
      </div>
    </div>
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
      <span className="texto-suave indicador-conexion">
        <span className="badge badge-live">
          <Circle size={10} fill="currentColor" aria-hidden="true" /> EN VIVO
        </span>{' '}
        · Actualizado hace {segundos} s
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
              <span className="ranking-roles-posicion" aria-hidden="true">
                {r.posicion}
              </span>
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
    <section className="tablero-seccion podio-seccion" aria-labelledby="titulo-podio">
      <h2 id="titulo-podio">Podio</h2>
      <div className="podio" role="group" aria-label="Podio">
        {top3.map((p) => (
          <div key={p.usuario_id} className={`podio-bloque podio-${p.posicion}`}>
            <span className="podio-avatar" aria-hidden="true">
              {iniciales(p.nombre)}
              <span className="podio-medalla">
                <Medal />
              </span>
            </span>
            <strong className="podio-nombre">{p.nombre}</strong>
            <span className="podio-rol">{p.rol_nombre}</span>
            <span className="podio-puntos">{formatoPuntaje(p.puntaje)} pts</span>
            <span className="podio-pedestal">
              <span className="podio-lugar">
                {p.posicion}
                <span className="solo-lector">.º lugar</span>
              </span>
              <span className="podio-porcentaje">{Math.round(p.porcentaje)}%</span>
            </span>
          </div>
        ))}
      </div>
    </section>
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
              <span className="ranking-completo-avatar" aria-hidden="true">
                {iniciales(p.nombre)}
              </span>
              <span className="ranking-completo-nombre">
                <strong>{p.nombre}</strong>
                <span className="tablero-texto-suave">
                  {p.rol_nombre} · {p.respondidas}/{p.respondidas + p.sin_responder} respondidas
                </span>
                <span className={`barra-avance-tablero barra-fina ${tierDeColor(p.porcentaje)}`}>
                  <span style={{ width: `${p.porcentaje}%` }} />
                </span>
              </span>
              <span className="ranking-completo-puntos">
                {formatoPuntaje(p.puntaje)} pts
                <small>{Math.round(p.porcentaje)}%</small>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
