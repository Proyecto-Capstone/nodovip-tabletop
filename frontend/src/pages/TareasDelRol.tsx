// PB-08: tareas del rol del participante en la sesión en vivo (prototipo P-04).
// Pregunta actual, tiempo restante y campo de respuesta. Se responde una vez:
// después queda bloqueada, igual que al vencer el tiempo.

import { useEffect, useState, type FormEvent } from 'react'
import { Check, Timer } from 'lucide-react'
import { ApiError } from '../api/client'
import type { VistaEnVivo } from '../api/enVivo'
import { responderTarea, rutaTareas, type TareaParticipante } from '../api/misSesiones'
import { Errores } from '../components/Etiquetas'
import { useGet } from '../lib/useGet'

export function TareasDelRol({
  sesionId,
  rolNombre,
  vista,
}: {
  sesionId: string
  rolNombre: string
  vista: VistaEnVivo
}) {
  // Cada cambio de la sesión (inject nuevo, pausa) vuelve a pedir las tareas.
  const marca = `${vista.version}-${vista.pausada}`
  const tareas = useGet<TareaParticipante[]>(rutaTareas(sesionId), marca)
  const [actualizadas, setActualizadas] = useState<Record<string, TareaParticipante>>({})
  // Mientras llega la consulta nueva se muestran las últimas: sin parpadeos y
  // sin perder lo que el participante está escribiendo.
  const [ultimas, setUltimas] = useState<TareaParticipante[]>()
  if (tareas.datos && tareas.datos !== ultimas) setUltimas(tareas.datos)
  const conocidas = tareas.datos ?? ultimas
  // PC-49: la tarea pendiente arriba; las ya cerradas debajo, la más reciente primero.
  const lista = (conocidas ?? [])
    .map((t) => actualizadas[t.id] ?? t)
    .sort(
      (a, b) =>
        Number(a.estado !== 'pendiente') - Number(b.estado !== 'pendiente') ||
        b.inject_orden - a.inject_orden,
    )

  if (tareas.errores) return <Errores errores={tareas.errores} />
  if (!conocidas) return null
  if (lista.length === 0) {
    return (
      <section className="tarjeta tarea-vivo">
        <h2>Tu tarea — {rolNombre}</h2>
        <p className="texto-suave">
          Todavía no hay tareas para tu rol. Aparecerán aquí cuando el moderador lance
          el inject correspondiente.
        </p>
      </section>
    )
  }

  // PC-49: no todos los roles tienen tarea en cada inject; se avisa para que no
  // parezca que falta algo.
  const sinTareaActual = !lista.some((t) => t.inject_orden === vista.inject_actual)

  return (
    <>
      {sinTareaActual && (
        <p className="tarjeta tarea-espera" role="status">
          No tienes tarea en el inject {vista.inject_actual}. Lee la evidencia: tu próxima tarea
          aparecerá aquí.
        </p>
      )}
      {lista.map((t) => (
        <TarjetaTarea
          key={t.id}
          sesionId={sesionId}
          rolNombre={rolNombre}
          tarea={t}
          pausada={vista.pausada}
          marca={marca}
          alResponder={(nueva) => setActualizadas((a) => ({ ...a, [nueva.id]: nueva }))}
          alConflicto={tareas.recargar}
        />
      ))}
    </>
  )
}

function TarjetaTarea({
  sesionId,
  rolNombre,
  tarea,
  pausada,
  marca,
  alResponder,
  alConflicto,
}: {
  sesionId: string
  rolNombre: string
  tarea: TareaParticipante
  pausada: boolean
  marca: string
  alResponder: (t: TareaParticipante) => void
  alConflicto: () => void
}) {
  const restantes = useCuentaRegresiva(
    tarea.segundos_restantes,
    pausada || tarea.estado !== 'pendiente',
    marca,
  )
  const [texto, setTexto] = useState('')
  const [elegidas, setElegidas] = useState<number[]>([])
  const [enviando, setEnviando] = useState(false)
  const [errores, setErrores] = useState<string[]>()

  const vencida = tarea.estado === 'vencida' || (tarea.estado === 'pendiente' && restantes <= 0)
  const bloqueada = tarea.estado === 'respondida' || vencida || pausada || enviando
  const listo = tarea.tipo === 'texto_libre' ? texto.trim().length > 0 : elegidas.length > 0
  let claseEstado = 'tarea-pendiente'
  if (tarea.estado === 'respondida') claseEstado = 'tarea-respondida'
  else if (vencida) claseEstado = 'tarea-vencida'

  const enviar = async (e: FormEvent) => {
    e.preventDefault()
    setEnviando(true)
    setErrores(undefined)
    try {
      const datos = tarea.tipo === 'texto_libre' ? { texto } : { opciones: elegidas }
      alResponder(await responderTarea(sesionId, tarea.id, datos))
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
      if (error instanceof ApiError && error.status === 409) alConflicto()
    } finally {
      setEnviando(false)
    }
  }

  const alternar = (i: number) =>
    setElegidas((a) => (a.includes(i) ? a.filter((x) => x !== i) : [...a, i]))

  return (
    <form className={`tarjeta tarea-vivo ${claseEstado}`} onSubmit={enviar}>
      <div className="tarea-vivo-cabecera">
        <div>
          <span className="badge inject-badge inject-1">Inject {tarea.inject_orden}</span>
          <h2>Tu tarea — {rolNombre}</h2>
        </div>
        {tarea.estado === 'pendiente' && !vencida && (
          <RelojTarea restantes={restantes} limite={tarea.tiempo_limite_segundos} />
        )}
        {tarea.estado === 'respondida' && (
          <span className="tarea-sello tarea-sello-ok">
            <Check size={14} aria-hidden="true" /> Respondida
          </span>
        )}
        {vencida && tarea.estado !== 'respondida' && (
          <span className="tarea-sello tarea-sello-vencida">
            <Timer size={14} aria-hidden="true" /> Sin tiempo
          </span>
        )}
      </div>
      <p className="tarea-vivo-enunciado">{tarea.enunciado}</p>

      {tarea.tipo === 'texto_libre' ? (
        tarea.respuesta ? (
          <p className="respuesta-enviada-texto">{tarea.respuesta.texto}</p>
        ) : (
          <label className="campo">
            <span className="solo-lector">Tu respuesta</span>
            <textarea
              rows={4}
              maxLength={5000}
              placeholder="Escribe tu respuesta…"
              value={texto}
              disabled={bloqueada}
              onChange={(e) => setTexto(e.target.value)}
            />
          </label>
        )
      ) : (
        <fieldset className="opciones-tarea" disabled={bloqueada}>
          <legend className="texto-suave">Marca todas las que correspondan</legend>
          {tarea.opciones.map((o, i) => {
            const marcada = tarea.respuesta
              ? tarea.respuesta.opciones_elegidas.includes(i)
              : elegidas.includes(i)
            return (
              <label key={i} className={marcada ? 'opcion-tarea marcada' : 'opcion-tarea'}>
                <input type="checkbox" checked={marcada} onChange={() => alternar(i)} />
                {o}
              </label>
            )
          })}
        </fieldset>
      )}

      <Errores errores={errores} />

      {tarea.estado === 'respondida' ? (
        <div className="alerta alerta-exito" role="status">
          <Check size={16} aria-hidden="true" /> Respuesta enviada. Ya no se puede modificar.
        </div>
      ) : vencida ? (
        <div className="alerta alerta-aviso" role="status">
          Se agotó el tiempo para esta tarea.
        </div>
      ) : (
        <div className="acciones-bloque">
          <button
            type="submit"
            className="boton boton-enviar"
            disabled={bloqueada || !listo}
          >
            {enviando ? 'Enviando…' : 'Enviar respuesta →'}
          </button>
        </div>
      )}
    </form>
  )
}

/** Anillo que se vacía con el tiempo de la tarea; en rojo los últimos 30 segundos. */
function RelojTarea({ restantes, limite }: { restantes: number; limite: number }) {
  const radio = 20
  const circunferencia = 2 * Math.PI * radio
  const fraccion = limite > 0 ? Math.max(0, Math.min(1, restantes / limite)) : 0
  return (
    <span
      className={restantes <= 30 ? 'reloj-tarea urgente' : 'reloj-tarea'}
      aria-label={`Tiempo restante: ${restantes} segundos`}
    >
      <svg viewBox="0 0 48 48" aria-hidden="true">
        <circle className="reloj-pista" cx="24" cy="24" r={radio} />
        <circle
          className="reloj-avance"
          cx="24"
          cy="24"
          r={radio}
          strokeDasharray={circunferencia}
          strokeDashoffset={circunferencia * (1 - fraccion)}
        />
      </svg>
      <span className="reloj-texto">
        <span className="reloj-etiqueta">Quedan</span>
        {formatoMinutos(restantes)}
      </span>
    </span>
  )
}

/** Segundos que quedan, contando hacia atrás localmente (se detiene en pausa). */
function useCuentaRegresiva(inicial: number, detenida: boolean, marca: string) {
  // Segundos descontados desde la última consulta. Se reinicia con cada cambio
  // de la sesión (marca), aunque el valor recibido sea el mismo.
  const [descontados, setDescontados] = useState({ marca, inicial, segundos: 0 })
  const vigente = descontados.marca === marca && descontados.inicial === inicial

  useEffect(() => {
    if (detenida) return
    const id = setInterval(
      () =>
        setDescontados((d) =>
          d.marca === marca && d.inicial === inicial
            ? { ...d, segundos: d.segundos + 1 }
            : { marca, inicial, segundos: 1 },
        ),
      1000,
    )
    return () => clearInterval(id)
  }, [detenida, marca, inicial])

  if (detenida || !vigente) return inicial
  return Math.max(0, inicial - descontados.segundos)
}

function formatoMinutos(segundos: number) {
  const m = Math.floor(segundos / 60)
  const s = segundos % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
