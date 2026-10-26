// PB-06: sesiones a las que el participante fue invitado (RNF-06/07: móvil y escritorio).

import { Link } from 'react-router-dom'
import { rutasMisSesiones, type MiSesion } from '../api/misSesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, InvitacionBadge, SinPermiso } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'
import { formatoDuracion, formatoFecha } from './disenador/comun'

export function MisSesionesPage() {
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:participar')
  const sesiones = useGet<MiSesion[]>(permitido ? rutasMisSesiones.lista : null, rol)

  if (!permitido) return <SinPermiso />

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Mis sesiones</h1>
          <p className="texto-suave">
            Ejercicios tabletop a los que te invitaron. Confirma tu asistencia en cada
            uno.
          </p>
        </div>
      </div>

      <Errores errores={sesiones.errores} />
      {sesiones.cargando && <Cargando />}
      {sesiones.datos?.length === 0 && (
        <p className="tarjeta vacio">
          Todavía no tienes invitaciones. Cuando un moderador te invite, la sesión
          aparecerá aquí y recibirás un correo.
        </p>
      )}
      <div className="lista-mis-sesiones">
        {sesiones.datos?.map((s) => (
          <Link key={s.id} to={`/mis-sesiones/${s.id}`} className="tarjeta tarjeta-sesion">
            <div className="fila-badges">
              <span className="tipo">{s.rol_nombre}</span>
              <InvitacionBadge estado={s.invitacion} />
            </div>
            <h2>{s.nombre}</h2>
            <p className="texto-suave">
              {formatoFecha(s.fecha_programada)}
              {s.duracion_minutos ? ` · ${formatoDuracion(s.duracion_minutos)}` : ''}
            </p>
            <p className="texto-suave">Moderador: {s.moderador_nombre}</p>
          </Link>
        ))}
      </div>
    </>
  )
}
