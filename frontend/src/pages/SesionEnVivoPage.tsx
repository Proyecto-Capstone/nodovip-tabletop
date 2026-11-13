// PB-07: el participante sigue la sesión en vivo (prototipo P-04, Figura 19).
// Recibe el inject actual por WebSocket; si pierde la conexión, se reconecta y
// recupera el estado. PB-08: las tareas de su rol y su respuesta.

import { Bell, BellOff, Clock, Users, Zap } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { rutasMisSesiones, type MiSesion } from '../api/misSesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { EstadoVivo } from '../components/EstadoVivo'
import { useAvisoInject } from '../lib/useAvisoInject'
import { formatoReloj, useCronometro, useEnVivo } from '../lib/useEnVivo'
import { useGet } from '../lib/useGet'
import { InjectActual } from './ConducirSesionPage'
import { AvisoInject, LineaDeTiempo } from './LineaDeTiempo'
import { ResumenDelParticipante } from './ResumenParticipante'
import { TareasDelRol } from './TareasDelRol'

export function SesionEnVivoPage() {
  const { id = '' } = useParams()
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:participar')
  const mia = useGet<MiSesion>(permitido ? rutasMisSesiones.sesion(id) : null, rol)
  const { vista, conexion, error, recibidaEn } = useEnVivo(permitido ? id : undefined)
  const segundos = useCronometro(vista, recibidaEn)
  const { aviso, cerrarAviso, sonido, alternarSonido } = useAvisoInject(vista)

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
  // Al terminar, el avance y el reloj ya no aportan: se muestra el resumen.
  const terminada = estado === 'finalizada'
  const avance = vista?.total_injects ? (100 * vista.inject_actual) / vista.total_injects : 0

  const totalInjects = vista?.total_injects ?? 0
  const injectActual = vista?.inject_actual ?? 0

  return (
    <div
      className={`sala-vivo ${estado === 'en_curso' ? 'sala-vivo-activa' : ''} ${terminada ? 'sala-vivo-resumen' : ''}`}
    >
      <div className="sala-cabecera">
        <div className="sala-titulo">
          <p className="sala-eyebrow">Sala del ejercicio</p>
          <h1>{mia.datos.nombre}</h1>
          <div className="chips">
            <span className="chip chip-rol">Rol: {mia.datos.rol_nombre}</span>
            <span className="chip">{mia.datos.escenario_nombre}</span>
          </div>
        </div>
        <div className="sala-cabecera-acciones">
          {!terminada && (
            <button
              type="button"
              className="boton boton-texto boton-sonido"
              aria-pressed={sonido}
              onClick={alternarSonido}
              title={sonido ? 'Silenciar el aviso de nuevos injects' : 'Activar el sonido'}
            >
              {sonido ? (
                <Bell size={16} aria-hidden="true" />
              ) : (
                <BellOff size={16} aria-hidden="true" />
              )}{' '}
              {sonido ? 'Sonido activado' : 'Silenciado'}
            </button>
          )}
          <EstadoVivo estado={estado} pausada={vista?.pausada ?? false} />
        </div>
      </div>

      <AvisoInject inject={aviso} onCerrar={cerrarAviso} />

      {!terminada && (
        <div className="sala-estado">
          <div className="sala-estado-avance">
            <span className="sala-estado-etiqueta">
              <Zap size={14} aria-hidden="true" />
              {`Inject ${injectActual} de ${vista?.total_injects ?? '…'}`}
            </span>
            <div
              className="pasos-inject"
              role="progressbar"
              aria-label="Avance de la sesión"
              aria-valuenow={Math.round(avance)}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              {Array.from({ length: totalInjects }, (_, i) => (
                <span
                  key={i}
                  className={
                    i + 1 < injectActual ? 'hecho' : i + 1 === injectActual ? 'actual' : undefined
                  }
                />
              ))}
            </div>
          </div>
          <div className="sala-estado-dato">
            <Clock size={16} aria-hidden="true" />
            <div>
              <span className="sala-estado-etiqueta">Tiempo transcurrido</span>
              <strong>{formatoReloj(segundos)}</strong>
            </div>
          </div>
          <div className="sala-estado-dato">
            <Users size={16} aria-hidden="true" />
            <div>
              <span className="sala-estado-etiqueta">En la sala</span>
              <strong>
                {vista
                  ? `${vista.total_conectados} ${vista.total_conectados === 1 ? 'conectado' : 'conectados'}`
                  : '…'}
              </strong>
            </div>
          </div>
        </div>
      )}

      {conexion === 'reconectando' && (
        <div className="alerta alerta-aviso" role="status">
          Se perdió la conexión. Reconectando…
        </div>
      )}
      <Errores errores={error ? [error] : undefined} />

      {estado === 'finalizada' ? (
        // PC-45: al terminar, su resultado y la retroalimentación de cada tarea.
        <ResumenDelParticipante sesionId={id} />
      ) : (
        <>
          {vista?.pausada && (
            <div className="alerta alerta-aviso" role="status">
              El moderador pausó la sesión. Espera a que la reanude.
            </div>
          )}
          {estado !== 'en_curso' && (
            <p className="tarjeta parrafo">
              La sesión todavía no empieza. Esta pantalla se actualizará sola cuando el moderador la
              inicie.
            </p>
          )}
          {estado === 'en_curso' && vista && (
            // PC-49: en escritorio, el escenario a la izquierda y las tareas a la derecha.
            <div className="sala-grid">
              <div className="sala-columna-escenario">
                <section className="tarjeta narrativa">
                  <h2>Narrativa del escenario</h2>
                  <InjectActual vista={vista} />
                </section>
                <LineaDeTiempo lanzados={vista.lanzados ?? []} />
              </div>
              <div className="sala-columna-tareas">
                <TareasDelRol sesionId={id} rolNombre={mia.datos.rol_nombre} vista={vista} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
