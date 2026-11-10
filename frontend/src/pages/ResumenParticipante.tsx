// PC-45: resumen personal del participante al terminar la sesión: su puntaje y
// posición, cada tarea con lo que respondió y la retroalimentación (criterios
// cumplidos y faltantes, opciones correctas, comentario del moderador), y las
// lecciones aprendidas si el moderador ya completó el debrief.

import { rutasDebrief, type ResumenParticipante, type TareaResumen } from '../api/debrief'
import { Cargando, Errores } from '../components/Etiquetas'
import { Lecciones } from '../components/Lecciones'
import { useGet } from '../lib/useGet'

const formatoPuntaje = (n: number) => n.toLocaleString('es-EC', { maximumFractionDigits: 2 })
const nivelDe = (porcentaje: number) =>
  porcentaje >= 70 ? 'verde' : porcentaje >= 40 ? 'naranja' : 'rojo'

export function ResumenDelParticipante({ sesionId }: { sesionId: string }) {
  const resumen = useGet<ResumenParticipante>(rutasDebrief.resumen(sesionId))
  if (resumen.errores) return <Errores errores={resumen.errores} />
  if (!resumen.datos) return <Cargando />
  const r = resumen.datos
  const respondidas = r.tareas.filter((t) => t.respondida).length

  return (
    <div className="resumen-participante">
      <section className="tarjeta resumen-hero" aria-labelledby="titulo-resultado">
        <div>
          <p className="resumen-etiqueta">La sesión terminó · ¡Gracias por participar!</p>
          <h2 id="titulo-resultado">Tu resultado como {r.rol_nombre}</h2>
          <p className="texto-suave">
            Respondiste {respondidas} de {r.tareas.length}{' '}
            {r.tareas.length === 1 ? 'tarea' : 'tareas'}.
          </p>
        </div>
        <div className="resumen-cifras">
          <div>
            <strong className={`texto-${nivelDe(r.porcentaje)}`}>{r.porcentaje} %</strong>
            <span className="texto-suave">
              {formatoPuntaje(r.puntaje)} / {r.maximo} pts
            </span>
          </div>
          <div>
            <strong>
              #{r.posicion}
              <small> de {r.total_participantes}</small>
            </strong>
            <span className="texto-suave">Posición</span>
          </div>
        </div>
      </section>

      <section className="tarjeta" aria-labelledby="titulo-retro">
        <h2 id="titulo-retro">Tus respuestas, inject por inject</h2>
        {r.tareas.length === 0 && (
          <p className="texto-suave">No se lanzaron tareas para tu rol en esta sesión.</p>
        )}
        <ol className="resumen-tareas">
          {r.tareas.map((t, i) => (
            <TareaConRetro key={i} t={t} />
          ))}
        </ol>
      </section>

      <section className="tarjeta" aria-labelledby="titulo-lecciones">
        <h2 id="titulo-lecciones">Lecciones aprendidas del ejercicio</h2>
        {r.lecciones ? (
          <Lecciones {...r.lecciones} />
        ) : (
          <p className="texto-suave">
            El moderador compartirá aquí las lecciones aprendidas y el plan de acción cuando
            complete el debrief.
          </p>
        )}
      </section>
    </div>
  )
}

function TareaConRetro({ t }: { t: TareaResumen }) {
  const porcentaje = t.puntaje_maximo ? (100 * t.puntaje) / t.puntaje_maximo : 0
  return (
    <li className="resumen-tarea">
      <div className="resumen-tarea-cabecera">
        <span className="badge inject-badge inject-0">Inject {t.inject_orden}</span>
        <span className="texto-suave">{t.inject_titulo}</span>
        <span className={`resumen-puntaje texto-${nivelDe(porcentaje)}`}>
          {formatoPuntaje(t.puntaje)} / {t.puntaje_maximo}
        </span>
      </div>
      <p className="resumen-enunciado">{t.enunciado}</p>

      {t.respondida ? (
        <div className="resumen-respuesta">
          <span className="texto-suave texto-chico">Tu respuesta</span>
          <p>{t.respuesta}</p>
        </div>
      ) : (
        <div className="alerta alerta-aviso">No respondiste esta tarea a tiempo.</div>
      )}

      <div className="resumen-retro">
        {t.aciertos.length > 0 && (
          <RetroLista clase="retro-bien" titulo="Cumpliste" items={t.aciertos} />
        )}
        {t.faltantes.length > 0 && (
          <RetroLista
            clase="retro-falta"
            titulo={t.respondida ? 'Te faltó mencionar' : 'Se esperaba'}
            items={t.faltantes}
          />
        )}
        {t.errores.length > 0 && (
          <RetroLista clase="retro-error" titulo="A revisar" items={t.errores} />
        )}
        {t.opciones_correctas.length > 0 && (
          <RetroLista
            clase="retro-bien"
            titulo={t.opciones_correctas.length === 1 ? 'Opción correcta' : 'Opciones correctas'}
            items={t.opciones_correctas}
          />
        )}
      </div>

      {t.ajuste_motivo && (
        <p className="resumen-comentario">
          <strong>Comentario del moderador:</strong> {t.ajuste_motivo}
        </p>
      )}
    </li>
  )
}

function RetroLista({ clase, titulo, items }: { clase: string; titulo: string; items: string[] }) {
  return (
    <div className={`retro ${clase}`}>
      <strong>{titulo}</strong>
      <ul>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </div>
  )
}
