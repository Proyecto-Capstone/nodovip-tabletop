// PB-07: el moderador conduce la sesión en vivo (prototipo P-05, Figura 20).
// Los comandos van por REST; el estado llega por WebSocket a todos, también
// a esta misma pantalla.
// PB-11: panel de control. Cuando el WebSocket avisa de una respuesta (o cambia
// el inject), recarga el avance por rol, los puntajes y las últimas respuestas.

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { comandoEnVivo, type ComandoEnVivo, type VistaEnVivo } from '../api/enVivo'
import {
  rutaPuntajes,
  rutaRespuestas,
  type PuntajesSesion,
  type RespuestaRegistrada,
} from '../api/respuestas'
import { rutas, type RolEjercicio } from '../api/escenarios'
import {
  rutasSesiones,
  type ParticipanteDisponible,
  type SesionDetalle,
} from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { EstadoVivo } from '../components/EstadoVivo'
import { nombreRol } from '../lib/etiquetas'
import { formatoReloj, useCronometro, useEnVivo } from '../lib/useEnVivo'
import { useGet, useGetVigente } from '../lib/useGet'
import {
  AvancePorRol,
  InjectsLanzados,
  LanzadoHace,
  ProgresoParticipantes,
  RespuestasRecientes,
} from './PanelAvance'

export function ConducirSesionPage() {
  const { id = '' } = useParams()
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:conducir')
  const sesion = useGet<SesionDetalle>(permitido ? rutasSesiones.sesion(id) : null, rol)
  const roles = useGet<RolEjercicio[]>(permitido ? rutas.roles : null, rol)
  const disponibles = useGet<ParticipanteDisponible[]>(
    permitido ? rutasSesiones.participantes : null,
    rol,
  )
  const envivo = useEnVivo(permitido ? id : undefined)

  if (!permitido) return <SinPermiso />
  if (sesion.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        Sesión no encontrada. <Link to="/sesiones">Volver a mis tabletops</Link>
      </div>
    )
  }
  const errores = sesion.errores ?? roles.errores
  if (errores) return <Errores errores={errores} />
  if (!sesion.datos || !roles.datos) return <Cargando />

  return (
    <Panel
      sesion={sesion.datos}
      roles={roles.datos}
      disponibles={disponibles.datos ?? []}
      {...envivo}
    />
  )
}

function Panel({
  sesion,
  roles,
  disponibles,
  vista,
  conexion,
  error,
  recibidaEn,
  avisosRespuesta,
}: {
  sesion: SesionDetalle
  roles: RolEjercicio[]
  disponibles: ParticipanteDisponible[]
} & ReturnType<typeof useEnVivo>) {
  const segundos = useCronometro(vista, recibidaEn)
  const { puede } = useSesion()
  const [enviando, setEnviando] = useState(false)
  const [errores, setErrores] = useState<string[]>()

  const ejecutar = async (comando: ComandoEnVivo) => {
    if (comando === 'cerrar' && !confirm('¿Cerrar la sesión? Los participantes ya no podrán continuar.')) {
      return
    }
    setEnviando(true)
    setErrores(undefined)
    try {
      await comandoEnVivo(sesion.id, comando)
    } catch (e) {
      setErrores(e instanceof ApiError ? e.errores : ['Error de conexión'])
    } finally {
      setEnviando(false)
    }
  }

  const estado = vista?.estado ?? sesion.estado
  const conectados = new Set(vista?.conectados ?? [])
  const participantesConectados = sesion.participantes.filter((p) =>
    conectados.has(p.usuario_id),
  ).length
  const persona = (id: string) => disponibles.find((u) => u.id === id)

  // Se recarga con cada respuesta nueva y cada cambio de inject o de estado.
  const conDatos = estado === 'en_curso' || estado === 'finalizada'
  const recarga = `${avisosRespuesta}-${vista?.inject_actual ?? 0}-${estado}`
  const puntajes = useGetVigente<PuntajesSesion>(
    conDatos ? rutaPuntajes(sesion.id) : null,
    recarga,
  )
  const respuestas = useGetVigente<RespuestaRegistrada[]>(
    conDatos ? rutaRespuestas(sesion.id) : null,
    recarga,
  )
  const avance = new Map((puntajes.datos?.participantes ?? []).map((p) => [p.usuario_id, p]))
  const recibidas = puntajes.datos?.participantes.reduce((n, p) => n + p.respondidas, 0) ?? 0
  const esperadas =
    puntajes.datos?.participantes.reduce((n, p) => n + p.respondidas + p.sin_responder, 0) ?? 0

  return (
    <div className="panel-vivo">
      <Link to="/sesiones" className="volver">
        ← Mis tabletops
      </Link>
      <div className="encabezado">
        <div>
          <h1>Panel del moderador: {sesion.nombre}</h1>
          <p className="texto-suave">
            {conexion === 'reconectando' ? 'Reconectando…' : 'Conectado en tiempo real'}
          </p>
        </div>
        <div className="acciones-fila">
          {(estado === 'en_curso' || estado === 'finalizada') && (
            <Link className="boton boton-texto" to={`/sesiones/${sesion.id}/respuestas`}>
              Ver respuestas
            </Link>
          )}
          {(estado === 'en_curso' || estado === 'finalizada') && puede('leaderboard:ver') && (
            <Link className="boton boton-texto" to={`/leaderboard/${sesion.id}`}>
              Ver leaderboard
            </Link>
          )}
          <EstadoVivo estado={estado} pausada={vista?.pausada ?? false} />
        </div>
      </div>

      <Errores
        errores={errores ?? (error ? [error] : undefined) ?? puntajes.errores ?? respuestas.errores}
      />

      <div className="metricas">
        <Metrica valor={formatoReloj(segundos)} nombre="Tiempo transcurrido" />
        <Metrica
          valor={`${participantesConectados}/${sesion.participantes.length}`}
          nombre="Participantes conectados"
          color="verde"
        />
        <Metrica
          valor={`${vista?.inject_actual ?? 0}/${sesion.injects.length}`}
          nombre="Inject actual"
          color="azul"
        />
        <Metrica
          valor={`${recibidas}/${esperadas}`}
          nombre="Respuestas recibidas"
          color="naranja"
        />
      </div>

      <div className="disenador-columnas">
        <ProgresoParticipantes
          injectActual={vista?.inject_actual ?? 0}
          filas={sesion.participantes.map((p) => {
            const suyo = avance.get(p.usuario_id)
            return {
              usuarioId: p.usuario_id,
              nombre: persona(p.usuario_id)?.nombre ?? suyo?.nombre ?? 'Participante',
              rolNombre: nombreRol(roles, p.rol_codigo),
              conectado: conectados.has(p.usuario_id),
              respondidas: suyo?.respondidas ?? 0,
              esperadas: suyo ? suyo.respondidas + suyo.sin_responder : 0,
            }
          })}
        />

        <section className="tarjeta">
          <h2>Control de sesión</h2>
          <InjectActual vista={vista} />
          {estado === 'en_curso' && vista?.inject_lanzado_en && (
            <LanzadoHace desde={vista.inject_lanzado_en} />
          )}
          <Controles estado={estado} vista={vista} enviando={enviando} ejecutar={ejecutar} />
          {conDatos && (
            <RespuestasRecientes sesionId={sesion.id} respuestas={respuestas.datos ?? []} />
          )}
        </section>
      </div>

      {conDatos && (
        <div className="disenador-columnas">
          <AvancePorRol
            roles={puntajes.datos?.roles ?? []}
            participantes={sesion.participantes}
            conectados={conectados}
          />
          <InjectsLanzados injects={sesion.injects} actual={vista?.inject_actual ?? 0} />
        </div>
      )}
    </div>
  )
}

function Controles({
  estado,
  vista,
  enviando,
  ejecutar,
}: {
  estado: string
  vista?: VistaEnVivo
  enviando: boolean
  ejecutar: (c: ComandoEnVivo) => void
}) {
  if (estado === 'finalizada') {
    return <p className="parrafo">La sesión terminó. El estado final quedó guardado.</p>
  }
  if (estado !== 'en_curso') {
    return (
      <div className="controles">
        <button
          type="button"
          className="boton boton-primario boton-grande"
          disabled={enviando || estado !== 'programada'}
          onClick={() => ejecutar('iniciar')}
        >
          ▶ Iniciar sesión
        </button>
        {estado === 'borrador' && (
          <p className="texto-suave">Programa la sesión en el diseñador antes de iniciarla.</p>
        )}
      </div>
    )
  }
  const siguiente = (vista?.inject_actual ?? 0) + 1
  const quedan = vista ? vista.inject_actual < vista.total_injects : false
  return (
    <div className="controles">
      <button
        type="button"
        className="boton boton-primario boton-grande"
        disabled={enviando || !quedan || vista?.pausada}
        onClick={() => ejecutar('lanzar-inject')}
      >
        {quedan ? `▶ Lanzar inject ${siguiente}` : 'Todos los injects lanzados'}
      </button>
      {vista?.pausada ? (
        <button
          type="button"
          className="boton boton-grande boton-pausa"
          disabled={enviando}
          onClick={() => ejecutar('reanudar')}
        >
          ▶ Reanudar
        </button>
      ) : (
        <button
          type="button"
          className="boton boton-grande boton-pausa"
          disabled={enviando}
          onClick={() => ejecutar('pausar')}
        >
          ⏸ Pausar
        </button>
      )}
      <button
        type="button"
        className="boton boton-grande boton-cerrar"
        disabled={enviando}
        onClick={() => ejecutar('cerrar')}
      >
        ✕ Cerrar sesión
      </button>
    </div>
  )
}

export function InjectActual({ vista }: { vista?: VistaEnVivo }) {
  if (!vista || vista.estado === 'programada' || vista.estado === 'borrador') {
    return (
      <div className="inject-vivo vacio-vivo">
        La sesión todavía no empieza.
      </div>
    )
  }
  if (!vista.inject) {
    return (
      <div className="inject-vivo vacio-vivo">
        Sesión iniciada. Todavía no se lanzó ningún inject.
      </div>
    )
  }
  return (
    <div className="inject-vivo">
      <span className="badge inject-badge inject-0">Inject {vista.inject.orden}</span>
      <h3>{vista.inject.titulo}</h3>
      <p className="parrafo">{vista.inject.descripcion}</p>
    </div>
  )
}

function Metrica({
  valor,
  nombre,
  color,
}: {
  valor: string
  nombre: string
  color?: 'verde' | 'azul' | 'naranja'
}) {
  return (
    <div className="tarjeta metrica">
      <strong className={color ? `metrica-${color}` : ''}>{valor}</strong>
      <span className="texto-suave">{nombre}</span>
    </div>
  )
}
