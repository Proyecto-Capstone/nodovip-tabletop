// PB-06: sesiones a las que el participante fue invitado (RNF-06/07: móvil y escritorio).
// PC-49: la sesión en vivo va primero con acceso directo a la sala, un resumen en
// indicadores y las finalizadas se recortan a las más recientes.

import { useState, type ReactNode } from 'react'
import { ArrowRight, CalendarClock, CheckCircle2, Circle, MailQuestion, Radio } from 'lucide-react'
import { Link } from 'react-router-dom'
import { rutasMisSesiones, type MiSesion } from '../api/misSesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, InvitacionBadge, SinPermiso } from '../components/Etiquetas'
import { Indicador } from '../components/Indicador'
import { useGet } from '../lib/useGet'
import { formatoDuracion, formatoFecha } from './disenador/comun'

const FINALIZADAS_VISIBLES = 10

export function MisSesionesPage() {
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:participar')
  const sesiones = useGet<MiSesion[]>(permitido ? rutasMisSesiones.lista : null, rol)
  const [verTodas, setVerTodas] = useState(false)

  if (!permitido) return <SinPermiso />

  const todas = sesiones.datos ?? []
  const enVivo = todas.filter((s) => s.estado === 'en_curso')
  // Próximas: la más cercana primero; las que no tienen fecha, al final.
  const proximas = todas
    .filter((s) => s.estado !== 'finalizada' && s.estado !== 'en_curso')
    .sort((a, b) => (a.fecha_programada ?? '9999').localeCompare(b.fecha_programada ?? '9999'))
  // PC-45: las finalizadas van aparte, la más reciente primero.
  const finalizadas = todas
    .filter((s) => s.estado === 'finalizada')
    .sort((a, b) => (b.fecha_programada ?? '').localeCompare(a.fecha_programada ?? ''))
  const porConfirmar = proximas.filter((s) => s.invitacion !== 'aceptada').length
  const finalizadasVisibles = verTodas ? finalizadas : finalizadas.slice(0, FINALIZADAS_VISIBLES)

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

      {todas.length > 0 && (
        <section className="indicadores" aria-label="Resumen de mis sesiones">
          <Indicador
            tono="rojo"
            icono={<Radio />}
            etiqueta="En vivo ahora"
            valor={enVivo.length}
            detalle={enVivo.length ? 'Entra a la sala para responder' : 'Ninguna en este momento'}
          />
          <Indicador
            tono="naranja"
            icono={<MailQuestion />}
            etiqueta="Por confirmar"
            valor={porConfirmar}
            detalle="Invitaciones sin confirmar"
          />
          <Indicador
            tono="azul"
            icono={<CalendarClock />}
            etiqueta="Próximas"
            valor={proximas.length}
            detalle={
              proximas[0]
                ? `La siguiente: ${formatoFecha(proximas[0].fecha_programada)}`
                : undefined
            }
          />
          <Indicador
            tono="verde"
            icono={<CheckCircle2 />}
            etiqueta="Finalizadas"
            valor={finalizadas.length}
            detalle="Con resultado y retroalimentación"
          />
        </section>
      )}

      {enVivo.length > 0 && (
        <section className="grupo-mis-sesiones" aria-labelledby="titulo-en-vivo">
          <h2 id="titulo-en-vivo" className="leaderboard-grupo-titulo">
            <span className="punto-vivo" aria-hidden="true" />
            En vivo ahora
          </h2>
          <div className="lista-mis-sesiones">
            {enVivo.map((s) => (
              <Link
                key={s.id}
                to={`/mis-sesiones/${s.id}/en-vivo`}
                className="tarjeta tarjeta-sesion tarjeta-sesion-vivo"
              >
                <div className="fila-badges">
                  <span className="tipo">{s.rol_nombre}</span>
                  <span className="badge badge-vivo">
                    <Circle size={10} fill="currentColor" aria-hidden="true" /> En vivo
                  </span>
                </div>
                <h3>{s.nombre}</h3>
                <p className="texto-suave">{s.escenario_nombre}</p>
                <p className="texto-suave">Moderador: {s.moderador_nombre}</p>
                <span className="entrar-sala">
                  Entrar a la sala <ArrowRight size={16} aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {proximas.length > 0 && <ListaSesiones titulo="Próximas" sesiones={proximas} />}

      {finalizadas.length > 0 && (
        <ListaSesiones
          titulo="Finalizadas"
          descripcion="Revisa tu resultado, la retroalimentación de cada tarea y las lecciones del ejercicio."
          sesiones={finalizadasVisibles}
        >
          {finalizadas.length > FINALIZADAS_VISIBLES && (
            <button
              type="button"
              className="boton boton-secundario ver-todas"
              onClick={() => setVerTodas((v) => !v)}
              aria-expanded={verTodas}
            >
              {verTodas ? 'Ver solo las más recientes' : `Ver todas (${finalizadas.length})`}
            </button>
          )}
        </ListaSesiones>
      )}
    </>
  )
}

function ListaSesiones({
  titulo,
  descripcion,
  sesiones,
  children,
}: {
  titulo: string
  descripcion?: string
  sesiones: MiSesion[]
  children?: ReactNode
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
      {children}
    </section>
  )
}
