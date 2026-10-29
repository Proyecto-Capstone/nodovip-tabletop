// PB-07: el participante sigue la sesión en vivo (prototipo P-04, Figura 19).
// Recibe el inject actual por WebSocket; si pierde la conexión, se reconecta y
// recupera el estado. Las tareas de su rol y la respuesta llegan con PB-08.

import { Link, useParams } from 'react-router-dom'
import { rutasMisSesiones, type MiSesion } from '../api/misSesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { formatoReloj, useCronometro, useEnVivo } from '../lib/useEnVivo'
import { useGet } from '../lib/useGet'
import { EstadoVivo, InjectActual } from './ConducirSesionPage'

export function SesionEnVivoPage() {
  const { id = '' } = useParams()
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:participar')
  const mia = useGet<MiSesion>(permitido ? rutasMisSesiones.sesion(id) : null, rol)
  const { vista, conexion, error, recibidaEn } = useEnVivo(permitido ? id : undefined)
  const segundos = useCronometro(vista, recibidaEn)

  if (!permitido) return <SinPermiso />
  if (mia.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        No encontramos esta sesión entre tus invitaciones.{' '}
        <Link to="/mis-sesiones">Ver mis sesiones</Link>
      </div>
    )
  }
  if (mia.errores) return <Errores errores={mia.errores} />
  if (!mia.datos) return <Cargando />

  const estado = vista?.estado ?? mia.datos.estado
  const avance = vista?.total_injects ? (100 * vista.inject_actual) / vista.total_injects : 0

  return (
    <div className="sala-vivo">
      <div className="sala-cabecera">
        <div>
          <h1>{mia.datos.nombre}</h1>
          <span className="chip chip-rol">Rol: {mia.datos.rol_nombre}</span>
        </div>
        <EstadoVivo estado={estado} pausada={vista?.pausada ?? false} />
      </div>

      <div
        className="barra-avance"
        role="progressbar"
        aria-label="Avance de la sesión"
        aria-valuenow={Math.round(avance)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span style={{ width: `${avance}%` }} />
      </div>
      <div className="sala-datos texto-suave">
        <span>
          Inject {vista?.inject_actual ?? 0} de {vista?.total_injects ?? '…'}
        </span>
        <span>{formatoReloj(segundos)}</span>
        <span>{vista ? `${vista.total_conectados} conectados` : ''}</span>
      </div>

      {conexion === 'reconectando' && (
        <div className="alerta alerta-aviso" role="status">
          Se perdió la conexión. Reconectando…
        </div>
      )}
      <Errores errores={error ? [error] : undefined} />

      {estado === 'finalizada' ? (
        <div className="alerta alerta-exito" role="status">
          La sesión terminó. ¡Gracias por participar!
        </div>
      ) : (
        <>
          {vista?.pausada && (
            <div className="alerta alerta-aviso" role="status">
              El moderador pausó la sesión. Espera a que la reanude.
            </div>
          )}
          {estado !== 'en_curso' && (
            <p className="tarjeta parrafo">
              La sesión todavía no empieza. Esta pantalla se actualizará sola cuando el
              moderador la inicie.
            </p>
          )}
          {estado === 'en_curso' && (
            <section className="tarjeta narrativa">
              <h2>Narrativa del escenario</h2>
              <InjectActual vista={vista} />
            </section>
          )}
        </>
      )}
    </div>
  )
}
