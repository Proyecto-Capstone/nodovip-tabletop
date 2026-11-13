// PC-49: panel «Ahora mismo» del Inicio. Muestra lo que el usuario tiene en
// curso o por delante según lo que su rol puede ver: el participante, sus
// ejercicios; el moderador, las sesiones que conduce; el administrador, las
// sesiones activas; el observador y el analista, los rankings en vivo.

import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { rutaSesionesLeaderboard, type SesionLeaderboard } from '../api/leaderboard'
import { rutasMisSesiones, type MiSesion } from '../api/misSesiones'
import { rutaSesionesMonitoreo, type ResumenMonitoreo } from '../api/monitoreo'
import { rutasSesiones, type SesionResumen } from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { useGet } from '../lib/useGet'
import { formatoFecha } from './disenador/comun'

interface Pendiente {
  id: string
  titulo: string
  detalle: string
  vivo: boolean
  fecha: string | null
  to: string
  accion: string
}

const MAXIMO = 3

/** Primero lo que está en vivo; después lo programado, el más cercano primero. */
function priorizar(lista: Pendiente[]) {
  return [...lista]
    .sort(
      (a, b) =>
        Number(b.vivo) - Number(a.vivo) || (a.fecha ?? '9999').localeCompare(b.fecha ?? '9999'),
    )
    .slice(0, MAXIMO)
}

type Fuente = 'participante' | 'moderador' | 'monitoreo' | 'leaderboard'

export function AhoraMismo() {
  const { rol, puede } = useSesion()
  let fuente: Fuente | null = null
  if (puede('sesiones:participar')) fuente = 'participante'
  else if (puede('sesiones:disenar')) fuente = 'moderador'
  else if (puede('sesiones:monitorear')) fuente = 'monitoreo'
  else if (puede('leaderboard:ver')) fuente = 'leaderboard'

  const mias = useGet<MiSesion[]>(fuente === 'participante' ? rutasMisSesiones.lista : null, rol)
  const disenadas = useGet<SesionResumen[]>(
    fuente === 'moderador' ? rutasSesiones.lista : null,
    rol,
  )
  const activas = useGet<ResumenMonitoreo>(
    fuente === 'monitoreo' ? rutaSesionesMonitoreo : null,
    rol,
  )
  const ranking = useGet<SesionLeaderboard[]>(
    fuente === 'leaderboard' ? rutaSesionesLeaderboard : null,
    rol,
  )

  let items: Pendiente[] | undefined
  let vacio = ''
  if (fuente === 'participante' && mias.datos) {
    items = priorizar(
      mias.datos
        .filter((s) => s.estado === 'en_curso' || s.estado === 'programada')
        .map((s) => ({
          id: s.id,
          titulo: s.nombre,
          detalle: `${s.rol_nombre} · ${formatoFecha(s.fecha_programada)}`,
          vivo: s.estado === 'en_curso',
          fecha: s.fecha_programada,
          to: s.estado === 'en_curso' ? `/mis-sesiones/${s.id}/en-vivo` : `/mis-sesiones/${s.id}`,
          accion:
            s.estado === 'en_curso'
              ? 'Entrar a la sala'
              : s.invitacion === 'aceptada'
                ? 'Ver detalles'
                : 'Confirmar asistencia',
        })),
    )
    vacio = 'No tienes ejercicios en curso ni programados. Cuando te inviten, aparecerán aquí.'
  } else if (fuente === 'moderador' && disenadas.datos) {
    items = priorizar(
      disenadas.datos
        .filter((s) => s.estado === 'en_curso' || s.estado === 'programada')
        .map((s) => ({
          id: s.id,
          titulo: s.nombre,
          detalle: `${s.total_participantes} participantes · ${formatoFecha(s.fecha_programada)}`,
          vivo: s.estado === 'en_curso',
          fecha: s.fecha_programada,
          to: `/sesiones/${s.id}/conducir`,
          accion: s.estado === 'en_curso' ? 'Volver a la sesión' : 'Conducir',
        })),
    )
    vacio = 'No tienes sesiones en curso ni programadas. Diseña un tabletop para empezar.'
  } else if (fuente === 'monitoreo' && activas.datos) {
    items = activas.datos.sesiones.slice(0, MAXIMO).map((s) => ({
      id: s.id,
      titulo: s.nombre,
      detalle: `${s.moderador_nombre} · inject ${s.inject_actual}/${s.total_injects} · ${s.conectados}/${s.invitados} conectados`,
      vivo: true,
      fecha: null,
      to: `/monitoreo/${s.id}`,
      accion: 'Ver en modo lectura',
    }))
    vacio = `No hay sesiones en curso. Cupo libre: ${activas.datos.maximo} sesiones simultáneas.`
  } else if (fuente === 'leaderboard' && ranking.datos) {
    items = ranking.datos
      .filter((s) => s.estado === 'en_curso')
      .slice(0, MAXIMO)
      .map((s) => ({
        id: s.id,
        titulo: s.nombre,
        detalle: `Inject ${s.inject_actual} de ${s.total_injects}`,
        vivo: true,
        fecha: null,
        to: `/leaderboard/${s.id}`,
        accion: 'Ver ranking en vivo',
      }))
    vacio = 'No hay sesiones en vivo. Los resultados de las finalizadas están en el leaderboard.'
  }

  if (!items) return null

  return (
    <section className="portada-ahora" aria-labelledby="titulo-ahora">
      <h2 id="titulo-ahora" className="portada-ahora-titulo">
        Ahora mismo
      </h2>
      {items.length === 0 ? (
        <p className="portada-ahora-vacio">{vacio}</p>
      ) : (
        <ul>
          {items.map((i) => (
            <li key={i.id} className={i.vivo ? 'vivo' : undefined}>
              <Link to={i.to}>
                <span className="portada-ahora-estado">{i.vivo ? 'En vivo' : 'Programada'}</span>
                <span className="portada-ahora-texto">
                  <strong>{i.titulo}</strong>
                  <span>{i.detalle}</span>
                </span>
                <span className="portada-ahora-accion">
                  {i.accion} <ArrowRight size={14} aria-hidden="true" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
