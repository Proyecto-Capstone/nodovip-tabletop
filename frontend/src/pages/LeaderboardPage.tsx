// PB-12: sesiones con leaderboard visibles para el usuario. Observador y
// Administrador ven cualquier sesión en curso o finalizada; el Moderador,
// solo las suyas.

import { Link } from 'react-router-dom'
import { rutaSesionesLeaderboard, type SesionLeaderboard } from '../api/leaderboard'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'

export function LeaderboardPage() {
  const { rol, puede } = useSesion()
  const permitido = puede('leaderboard:ver')
  const sesiones = useGet<SesionLeaderboard[]>(
    permitido ? rutaSesionesLeaderboard : null,
    rol,
  )

  if (!permitido) return <SinPermiso />

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Leaderboard</h1>
          <p className="texto-suave">
            Ranking en vivo por participante y por rol, de las sesiones en curso o
            finalizadas.
          </p>
        </div>
      </div>

      <Errores errores={sesiones.errores} />
      {sesiones.cargando && <Cargando />}
      {sesiones.datos?.length === 0 && (
        <p className="tarjeta vacio">
          No hay sesiones en curso ni finalizadas con leaderboard todavía.
        </p>
      )}
      <div className="lista-mis-sesiones">
        {sesiones.datos?.map((s) => (
          <Link key={s.id} to={`/leaderboard/${s.id}`} className="tarjeta tarjeta-sesion">
            <div className="fila-badges">
              <EstadoSesionBadge estado={s.estado} />
              {s.estado === 'en_curso' && <span className="badge badge-live">● EN VIVO</span>}
            </div>
            <h2>{s.nombre}</h2>
            <p className="texto-suave">
              Inject {s.inject_actual}/{s.total_injects}
            </p>
          </Link>
        ))}
      </div>
    </>
  )
}
