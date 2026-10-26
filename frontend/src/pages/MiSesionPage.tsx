// PB-06: el enlace del correo llega aquí (tras iniciar sesión). El participante
// ve su sesión y su rol, y confirma su asistencia. La vista en vivo llega con PB-08.

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { aceptarInvitacion, rutasMisSesiones, type MiSesion } from '../api/misSesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, InvitacionBadge, SinPermiso } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'
import { formatoDuracion, formatoFecha } from './disenador/comun'

export function MiSesionPage() {
  const { id = '' } = useParams()
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:participar')
  const consulta = useGet<MiSesion>(permitido ? rutasMisSesiones.sesion(id) : null, rol)
  const [aceptada, setAceptada] = useState<MiSesion>()
  const [errores, setErrores] = useState<string[]>()
  const [enviando, setEnviando] = useState(false)

  if (!permitido) return <SinPermiso />
  if (consulta.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        No encontramos esta sesión entre tus invitaciones. Revisa que hayas entrado con
        la cuenta a la que llegó el correo. <Link to="/mis-sesiones">Ver mis sesiones</Link>
      </div>
    )
  }
  if (consulta.errores) return <Errores errores={consulta.errores} />
  const s = aceptada ?? consulta.datos
  if (!s) return <Cargando />

  const aceptar = async () => {
    setEnviando(true)
    setErrores(undefined)
    try {
      setAceptada(await aceptarInvitacion(s.id))
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="mi-sesion">
      <Link to="/mis-sesiones" className="volver">
        ← Mis sesiones
      </Link>
      <div className="fila-badges">
        <span className="tipo">Ejercicio tabletop</span>
        <InvitacionBadge estado={s.invitacion} />
      </div>
      <h1>{s.nombre}</h1>

      <Errores errores={errores} />

      <section className="tarjeta tu-rol">
        <p className="texto-suave">Tu rol en este ejercicio</p>
        <p className="rol-destacado">{s.rol_nombre}</p>
      </section>

      <section className="tarjeta">
        <dl className="datos-sesion">
          <div>
            <dt>Fecha</dt>
            <dd>{formatoFecha(s.fecha_programada)}</dd>
          </div>
          {s.duracion_minutos !== null && (
            <div>
              <dt>Duración</dt>
              <dd>{formatoDuracion(s.duracion_minutos)}</dd>
            </div>
          )}
          <div>
            <dt>Moderador</dt>
            <dd>{s.moderador_nombre}</dd>
          </div>
          <div>
            <dt>Participantes</dt>
            <dd>{s.total_participantes}</dd>
          </div>
        </dl>
        {s.escenario_nombre && (
          <>
            <h2>Escenario: {s.escenario_nombre}</h2>
            <p className="parrafo">{s.escenario_descripcion}</p>
          </>
        )}
      </section>

      {s.invitacion === 'aceptada' ? (
        <div className="alerta alerta-exito" role="status">
          Confirmaste tu asistencia. El día de la sesión entra desde aquí: las tareas de
          tu rol aparecerán cuando el moderador inicie el ejercicio.
        </div>
      ) : (
        <button
          type="button"
          className="boton boton-primario boton-bloque"
          disabled={enviando}
          onClick={aceptar}
        >
          {enviando ? 'Confirmando…' : 'Confirmar asistencia'}
        </button>
      )}
    </div>
  )
}
