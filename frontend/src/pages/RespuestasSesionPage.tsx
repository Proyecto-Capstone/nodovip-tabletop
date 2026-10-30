// PB-09: registro trazable de las respuestas de una sesión, para el moderador.
// Solo lectura: las respuestas registradas no se pueden modificar ni borrar.
// PB-10: puntaje automático de cada respuesta, ajuste manual con motivo (queda en
// el historial) y puntaje acumulado por participante y por rol.

import { Fragment, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  ajustarPuntaje,
  rutaPuntajes,
  rutaRespuestas,
  type PuntajesSesion,
  type RespuestaRegistrada,
} from '../api/respuestas'
import { rutasSesiones, type SesionDetalle } from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'

const formatoHora = (iso: string) =>
  new Date(iso).toLocaleString('es-EC', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

const formatoSegundos = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

/** 7.5 → "7,5"; 10 → "10". */
const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })

const COLUMNAS = 5

export function RespuestasSesionPage() {
  const { id = '' } = useParams()
  const { rol, puede } = useSesion()
  const sesion = useGet<SesionDetalle>(rutasSesiones.sesion(id), rol)
  const respuestas = useGet<RespuestaRegistrada[]>(rutaRespuestas(id), rol)
  const puntajes = useGet<PuntajesSesion>(rutaPuntajes(id), rol)
  const [rolFiltro, setRolFiltro] = useState('')
  const [injectFiltro, setInjectFiltro] = useState('')
  const [ajustando, setAjustando] = useState<string>()

  if (sesion.status === 404 || respuestas.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        Sesión no encontrada. <Link to="/sesiones">Volver a mis tabletops</Link>
      </div>
    )
  }

  const actualizar = () => {
    respuestas.recargar()
    puntajes.recargar()
  }
  const todas = respuestas.datos ?? []
  const roles = [...new Map(todas.map((r) => [r.rol_codigo, r.rol_nombre])).entries()]
  const injects = [...new Map(todas.map((r) => [r.inject_orden, r.inject_titulo])).entries()].sort(
    ([a], [b]) => a - b,
  )
  const visibles = todas.filter(
    (r) =>
      (!rolFiltro || r.rol_codigo === rolFiltro) &&
      (!injectFiltro || String(r.inject_orden) === injectFiltro),
  )

  return (
    <>
      <Link to="/sesiones" className="volver">
        ← Mis tabletops
      </Link>
      <div className="encabezado">
        <div>
          <h1>Respuestas y puntajes</h1>
          <p className="texto-suave">
            {sesion.datos?.nombre ?? '…'} · {todas.length}{' '}
            {todas.length === 1 ? 'respuesta' : 'respuestas'}, en orden de llegada con la hora del
            servidor.
          </p>
        </div>
        <div className="acciones-fila">
          {sesion.datos?.estado === 'en_curso' && (
            <Link className="boton boton-texto" to={`/sesiones/${id}/conducir`}>
              Volver al panel
            </Link>
          )}
          {puede('leaderboard:ver') &&
            (sesion.datos?.estado === 'en_curso' || sesion.datos?.estado === 'finalizada') && (
              <Link className="boton boton-texto" to={`/leaderboard/${id}`}>
                Ver leaderboard
              </Link>
            )}
          <button type="button" className="boton boton-texto" onClick={actualizar}>
            Actualizar
          </button>
        </div>
      </div>

      <p className="texto-suave nota-solo-lectura">
        🔒 Solo lectura: una respuesta registrada no se puede modificar ni borrar. Un ajuste de
        puntaje se agrega al historial; la evaluación automática original se conserva.
      </p>

      {puntajes.datos && <PuntajesAcumulados puntajes={puntajes.datos} />}

      {todas.length > 0 && (
        <div className="tarjeta filtros">
          <label className="campo">
            Rol
            <select value={rolFiltro} onChange={(e) => setRolFiltro(e.target.value)}>
              <option value="">Todos</option>
              {roles.map(([codigo, nombre]) => (
                <option key={codigo} value={codigo}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            Inject
            <select value={injectFiltro} onChange={(e) => setInjectFiltro(e.target.value)}>
              <option value="">Todos</option>
              {injects.map(([orden, titulo]) => (
                <option key={orden} value={orden}>
                  {orden}. {titulo}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <Errores errores={respuestas.errores ?? sesion.errores ?? puntajes.errores} />
      {respuestas.cargando && !respuestas.datos && <Cargando />}

      {respuestas.datos && visibles.length === 0 && (
        <div className="tarjeta vacio">
          {todas.length === 0
            ? 'Todavía no hay respuestas registradas en esta sesión.'
            : 'No hay respuestas con esos filtros.'}
        </div>
      )}

      {visibles.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla tabla-respuestas">
            <thead>
              <tr>
                <th>Recibida</th>
                <th>Participante</th>
                <th>Tarea</th>
                <th>Respuesta</th>
                <th>Puntaje</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((r) => (
                <Fragment key={r.id}>
                  <tr>
                    <td className="sin-salto">
                      {formatoHora(r.recibida_en)}
                      <div className="texto-suave" title="Tiempo usado / límite">
                        {formatoSegundos(r.segundos_usados)} /{' '}
                        {formatoSegundos(r.tiempo_limite_segundos)}
                      </div>
                    </td>
                    <td>
                      {r.participante_nombre}
                      <div className="texto-suave">{r.participante_correo}</div>
                      <span className="chip chip-rol">{r.rol_nombre}</span>
                    </td>
                    <td className="celda-tarea">
                      <div className="texto-suave sin-salto">
                        {r.inject_orden}. {r.inject_titulo}
                      </div>
                      {r.tarea_enunciado}
                    </td>
                    <td className="respuesta-registrada">
                      {r.tipo === 'texto_libre' ? (
                        r.texto
                      ) : (
                        <ul>
                          {r.opciones_elegidas_texto.map((o) => (
                            <li key={o}>{o}</li>
                          ))}
                        </ul>
                      )}
                    </td>
                    <td className="celda-puntaje">
                      <Puntaje respuesta={r} />
                      {ajustando !== r.id && (
                        <button
                          type="button"
                          className="boton boton-texto"
                          onClick={() => setAjustando(r.id)}
                        >
                          Ajustar
                        </button>
                      )}
                    </td>
                  </tr>
                  {ajustando === r.id && (
                    <tr className="fila-ajuste">
                      <td colSpan={COLUMNAS}>
                        <FormularioAjuste
                          sesionId={id}
                          respuesta={r}
                          alCerrar={() => setAjustando(undefined)}
                          alGuardar={() => {
                            setAjustando(undefined)
                            actualizar()
                          }}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function Puntaje({ respuesta: r }: { respuesta: RespuestaRegistrada }) {
  const ajustado = r.ajustes.length > 0
  return (
    <>
      <strong className="sin-salto">
        {formatoPuntaje(r.puntaje)} / {r.puntaje_maximo}
      </strong>
      {ajustado && (
        <div className="texto-suave sin-salto">
          <span className="badge badge-ajustado">Ajustado</span> auto:{' '}
          {formatoPuntaje(r.puntaje_automatico)}
        </div>
      )}
      <details className="detalle-evaluacion">
        <summary>Detalle</summary>
        <ul>
          <li>Completitud: {Math.round(r.completitud * 100)} %</li>
          <li>Precisión: {Math.round(r.precision * 100)} %</li>
          <li>Tiempo: {Math.round(r.tiempo * 100)} %</li>
          {r.aciertos.map((a) => (
            <li key={`a-${a}`} className="texto-exito">
              ✓ {a}
            </li>
          ))}
          {r.faltantes.map((f) => (
            <li key={`f-${f}`} className="texto-suave">
              ✗ Falta: {f}
            </li>
          ))}
          {r.errores.map((e) => (
            <li key={`e-${e}`} className="texto-peligro">
              ⚠ {e}
            </li>
          ))}
        </ul>
        {ajustado && (
          <>
            <strong>Historial de ajustes</strong>
            <ol>
              {r.ajustes.map((a) => (
                <li key={a.id}>
                  {formatoHora(a.creado_en)}: {formatoPuntaje(a.puntaje_anterior)} →{' '}
                  {formatoPuntaje(a.puntaje_nuevo)}. «{a.motivo}»
                </li>
              ))}
            </ol>
          </>
        )}
      </details>
    </>
  )
}

function FormularioAjuste({
  sesionId,
  respuesta,
  alCerrar,
  alGuardar,
}: {
  sesionId: string
  respuesta: RespuestaRegistrada
  alCerrar: () => void
  alGuardar: () => void
}) {
  const [puntaje, setPuntaje] = useState(String(respuesta.puntaje))
  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [errores, setErrores] = useState<string[]>()

  const guardar = async (e: FormEvent) => {
    e.preventDefault()
    setEnviando(true)
    setErrores(undefined)
    try {
      await ajustarPuntaje(sesionId, respuesta.id, { puntaje: Number(puntaje), motivo })
      alGuardar()
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="formulario-ajuste" onSubmit={guardar}>
      <strong>
        Ajustar el puntaje de {respuesta.participante_nombre} (máximo {respuesta.puntaje_maximo})
      </strong>
      <div className="campos-ajuste">
        <label className="campo">
          Nuevo puntaje
          <input
            type="number"
            min={0}
            max={respuesta.puntaje_maximo}
            step={0.25}
            required
            value={puntaje}
            onChange={(e) => setPuntaje(e.target.value)}
          />
        </label>
        <label className="campo campo-motivo">
          Motivo del ajuste
          <textarea
            rows={2}
            maxLength={1000}
            required
            placeholder="Por qué cambias el puntaje (queda registrado)"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
        </label>
      </div>
      <Errores errores={errores} />
      <div className="acciones-fila">
        <button type="submit" className="boton boton-primario" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Guardar ajuste'}
        </button>
        <button type="button" className="boton boton-texto" onClick={alCerrar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

function PuntajesAcumulados({ puntajes }: { puntajes: PuntajesSesion }) {
  return (
    <section className="tarjeta puntajes-acumulados" aria-labelledby="titulo-acumulado">
      <h2 id="titulo-acumulado">Puntaje acumulado</h2>
      <p className="texto-suave">
        Sobre las tareas de los injects ya lanzados. Una tarea sin responder suma 0.
      </p>
      <div className="tablas-acumulado">
        <div className="tabla-contenedor">
          <table className="tabla">
            <caption>Por participante</caption>
            <thead>
              <tr>
                <th>Participante</th>
                <th>Puntaje</th>
                <th>Respondidas</th>
              </tr>
            </thead>
            <tbody>
              {puntajes.participantes.map((p) => (
                <tr key={p.usuario_id}>
                  <td>
                    {p.nombre}
                    <div className="texto-suave">{p.rol_nombre}</div>
                  </td>
                  <td className="sin-salto">
                    <strong>{formatoPuntaje(p.puntaje)}</strong> / {p.maximo} ({p.porcentaje} %)
                  </td>
                  <td className="sin-salto">
                    {p.respondidas} de {p.respondidas + p.sin_responder}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="tabla-contenedor">
          <table className="tabla">
            <caption>Por rol</caption>
            <thead>
              <tr>
                <th>Rol</th>
                <th>Puntaje</th>
              </tr>
            </thead>
            <tbody>
              {puntajes.roles.map((r) => (
                <tr key={r.rol_codigo}>
                  <td>
                    {r.rol_nombre}
                    <div className="texto-suave">
                      {r.participantes} {r.participantes === 1 ? 'participante' : 'participantes'}
                    </div>
                  </td>
                  <td className="sin-salto">
                    <strong>{formatoPuntaje(r.puntaje)}</strong> / {r.maximo} ({r.porcentaje} %)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
