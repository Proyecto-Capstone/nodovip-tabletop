// PB-06: sesiones a las que el participante fue invitado (RNF-06/07: móvil y escritorio).

import { Circle } from 'lucide-react'
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

  // PC-45: las finalizadas van aparte, la más reciente primero.
  const todas = sesiones.datos ?? []
  const proximas = todas.filter((s) => s.estado !== 'finalizada')
  const finalizadas = todas
    .filter((s) => s.estado === 'finalizada')
    .sort((a, b) => (b.fecha_programada ?? '').localeCompare(a.fecha_programada ?? ''))

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Mis sesiones</h1>
          <p className="texto-suave">
            Ejercicios tabletop a los que te invitaron. Confirma tu asistencia y, al terminar,
            revisa tu resultado.
          </p>
        </div>
      </div>

      <Errores errores={sesiones.errores} />
      {sesiones.cargando && <Cargando />}
      {sesiones.datos?.length === 0 && (
        <p className="tarjeta vacio">
          Todavía no tienes invitaciones. Cuando un moderador te invite, la sesión aparecerá aquí y
          recibirás un correo.
        </p>
      )}
      {proximas.length > 0 && <ListaSesiones titulo="Próximas y en curso" sesiones={proximas} />}
      {finalizadas.length > 0 && (
        <ListaSesiones
          titulo="Finalizadas"
          descripcion="Revisa tu resultado, la retroalimentación de cada tarea y las lecciones del ejercicio."
          sesiones={finalizadas}
        />
      )}
    </>
  )
}

function ListaSesiones({
  titulo,
  descripcion,
  sesiones,
}: {
  titulo: string
  descripcion?: string
  sesiones: MiSesion[]
}) {
  return (
    <section className="grupo-mis-sesiones" aria-label={titulo}>
      <h2 className="titulo-grupo">{titulo}</h2>
      {descripcion && <p className="texto-suave texto-chico">{descripcion}</p>}
      <div className="lista-mis-sesiones">
        {sesiones.map((s) => (
          <Link key={s.id} to={`/mis-sesiones/${s.id}`} className="tarjeta tarjeta-sesion">
            <div className="fila-badges">
              <span className="tipo">{s.rol_nombre}</span>
              {s.estado === 'finalizada' ? (
                <span className="badge debrief-completado">Finalizada</span>
              ) : s.estado === 'en_curso' ? (
                <span className="badge badge-vivo">
                  <Circle size={10} fill="currentColor" aria-hidden="true" /> En vivo
                </span>
              ) : (
                <InvitacionBadge estado={s.invitacion} />
              )}
            </div>
            <h3>{s.nombre}</h3>
            <p className="texto-suave">
              {formatoFecha(s.fecha_programada)}
              {s.duracion_minutos ? ` · ${formatoDuracion(s.duracion_minutos)}` : ''}
            </p>
            <p className="texto-suave">Moderador: {s.moderador_nombre}</p>
          </Link>
        ))}
      </div>
    </section>
  )
}
