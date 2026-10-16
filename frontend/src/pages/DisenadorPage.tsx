// PB-05: diseñador de tabletop en 6 pasos (prototipo P-03, Figura 18).
// El paso 1 (elegir escenario) está en NuevaSesionPage; aquí se edita el
// borrador que nació de ese escenario. Cada cambio de paso guarda el borrador.

import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { rutas, type EscenarioDetalle, type RolEjercicio } from '../api/escenarios'
import {
  aDiseno,
  guardarSesion,
  programarSesion,
  rutasSesiones,
  type ParticipanteDisponible,
  type SesionDetalle,
  type SesionDiseno,
} from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'
import { formatoFecha, limpiarDiseno, pasosCompletos, PASOS } from './disenador/comun'
import { PasoProgramar } from './disenador/PasoProgramar'
import { PasoPuntuacion } from './disenador/PasoPuntuacion'
import { PasoRoles } from './disenador/PasoRoles'
import { PasosDiseno } from './disenador/PasosDiseno'
import { PasoTareas } from './disenador/PasoTareas'

const TITULOS = [
  'Seleccionar escenario',
  'Configurar roles',
  'Asignar tareas e injects por rol',
  'Criterios de puntuación',
  'Programar sesión',
  'Enviar invitaciones',
]

export function DisenadorPage() {
  const { id = '' } = useParams()
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:disenar')
  const sesion = useGet<SesionDetalle>(permitido ? rutasSesiones.sesion(id) : null, rol)
  const roles = useGet<RolEjercicio[]>(permitido ? rutas.roles : null, rol)
  const disponibles = useGet<ParticipanteDisponible[]>(
    permitido ? rutasSesiones.participantes : null,
    rol,
  )
  const escenario = useGet<EscenarioDetalle>(
    sesion.datos ? rutas.escenario(sesion.datos.escenario_id) : null,
    rol,
  )

  if (!permitido) return <SinPermiso />
  if (sesion.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        Sesión no encontrada. <Link to="/sesiones">Volver a mis tabletops</Link>
      </div>
    )
  }
  const errores = sesion.errores ?? roles.errores ?? disponibles.errores
  if (errores) return <Errores errores={errores} />
  if (!sesion.datos || !roles.datos || !disponibles.datos) return <Cargando />

  return (
    <Asistente
      key={id}
      inicial={sesion.datos}
      roles={roles.datos}
      disponibles={disponibles.datos}
      escenario={escenario.datos?.nombre ?? '…'}
    />
  )
}

function Asistente({
  inicial,
  roles,
  disponibles,
  escenario,
}: {
  inicial: SesionDetalle
  roles: RolEjercicio[]
  disponibles: ParticipanteDisponible[]
  escenario: string
}) {
  const [parametros, setParametros] = useSearchParams()
  const paso = Math.min(Math.max(Number(parametros.get('paso')) || 2, 1), 6)
  const [guardada, setGuardada] = useState(inicial)
  const [d, setD] = useState<SesionDiseno>(() => aDiseno(inicial))
  const [cambiado, setCambiado] = useState(false)
  const [errores, setErrores] = useState<string[]>()
  const [aviso, setAviso] = useState<string>()
  const [enviando, setEnviando] = useState(false)

  const editable = guardada.estado === 'borrador' || guardada.estado === 'programada'
  const cambiar = (cambio: (d: SesionDiseno) => SesionDiseno) => {
    setD(cambio)
    setCambiado(true)
    setAviso(undefined)
  }

  const aplicar = (s: SesionDetalle) => {
    setGuardada(s)
    setD(aDiseno(s))
    setCambiado(false)
  }

  /** Guarda el borrador. Devuelve false si el backend rechazó el diseño. */
  const guardar = async (): Promise<boolean> => {
    if (!editable) return true
    setEnviando(true)
    setErrores(undefined)
    try {
      aplicar(await guardarSesion(guardada.id, limpiarDiseno(d)))
      return true
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return false
    } finally {
      setEnviando(false)
    }
  }

  const irA = async (destino: number) => {
    if (cambiado && !(await guardar())) return
    setAviso(undefined)
    setParametros({ paso: String(destino) })
    window.scrollTo({ top: 0 })
  }

  const guardarBorrador = async () => {
    if (await guardar()) {
      setAviso(guardada.estado === 'borrador' ? 'Borrador guardado.' : 'Cambios guardados.')
    }
  }

  const programar = async () => {
    if (cambiado && !(await guardar())) return
    setEnviando(true)
    setErrores(undefined)
    try {
      aplicar(await programarSesion(guardada.id))
      setAviso('Sesión programada. Queda lista para iniciarse en la fecha indicada.')
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
    } finally {
      setEnviando(false)
    }
  }

  const props = { d, cambiar, roles, disponibles }

  return (
    <div className="disenador">
      <PasosDiseno
        actual={paso}
        completos={pasosCompletos(d)}
        alElegir={irA}
      />

      <div className="disenador-contenido">
        <Link to="/sesiones" className="volver">
          ← Mis tabletops
        </Link>
        <div className="encabezado">
          <div>
            <h1>
              Paso {paso} — {TITULOS[paso - 1]}
            </h1>
            <p className="texto-suave">
              {`Escenario: ${escenario} | Sesión: ${formatoFecha(d.fecha_programada)}`}
            </p>
          </div>
          <EstadoSesionBadge estado={guardada.estado} />
        </div>

        <Errores errores={errores} />
        {aviso && (
          <div className="alerta alerta-exito" role="status">
            {aviso}
          </div>
        )}
        {!editable && (
          <div className="alerta alerta-aviso">
            La sesión ya empezó o terminó: el diseño solo se puede consultar.
          </div>
        )}

        <fieldset className="sin-borde" disabled={!editable || enviando}>
          {paso === 1 && (
            <section className="tarjeta">
              <h2>Escenario base</h2>
              <p className="parrafo">
                Esta sesión usa una copia de <strong>{escenario}</strong>. Los cambios
                que hagas aquí no modifican el escenario de la biblioteca.
              </p>
              <Link to="/sesiones/nueva">Diseñar otra sesión con un escenario distinto</Link>
            </section>
          )}
          {paso === 2 && <PasoRoles {...props} />}
          {paso === 3 && <PasoTareas {...props} />}
          {paso === 4 && <PasoPuntuacion {...props} />}
          {paso === 5 && <PasoProgramar {...props} guardada={guardada} />}
          {paso === 6 && (
            <section className="tarjeta">
              <h2>Invitaciones</h2>
              <p className="parrafo">
                El envío de invitaciones por correo a los participantes llega con
                PB-06. Por ahora, programa la sesión en el paso 5.
              </p>
            </section>
          )}
        </fieldset>

        <div className="navegacion-pasos">
          <button
            type="button"
            className="boton"
            disabled={paso <= 1 || enviando}
            onClick={() => irA(paso - 1)}
          >
            ← Paso anterior
          </button>
          {editable && (
            <button
              type="button"
              className="boton boton-texto"
              disabled={enviando}
              onClick={guardarBorrador}
            >
              {guardada.estado === 'borrador' ? 'Guardar borrador' : 'Guardar cambios'}
            </button>
          )}
          {paso === 5 && guardada.estado === 'borrador' ? (
            <button
              type="button"
              className="boton boton-primario"
              disabled={enviando}
              onClick={programar}
            >
              Confirmar y programar
            </button>
          ) : (
            <button
              type="button"
              className="boton boton-primario"
              disabled={paso >= PASOS.length || enviando}
              onClick={() => irA(paso + 1)}
            >
              Paso siguiente →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
