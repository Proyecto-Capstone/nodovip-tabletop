// Paso 3: injects de la sesión y tareas de cada rol en cada inject (CU-03.3).

import { useState } from 'react'
import type { Nivel } from '../../api/escenarios'
import type { SesionDiseno, TareaSesion, TipoTarea } from '../../api/sesiones'
import { ETIQUETA_NIVEL, NIVELES, nombreRol } from '../../lib/etiquetas'
import {
  ETIQUETA_TIPO_TAREA,
  nuevoId,
  participanteDe,
  tareaCompleta,
  tareaNueva,
  type PropsPaso,
} from './comun'

export function PasoTareas(props: PropsPaso) {
  const { d, roles, disponibles } = props
  const [rolActivo, setRolActivo] = useState(d.roles[0] ?? '')
  const rol = d.roles.includes(rolActivo) ? rolActivo : (d.roles[0] ?? '')

  if (d.roles.length === 0) {
    return (
      <div className="alerta alerta-aviso">
        Primero elige los roles en el paso 2.
      </div>
    )
  }

  const nombreParticipante = (codigo: string) =>
    disponibles.find((u) => u.id === participanteDe(d, codigo))?.nombre

  return (
    <>
      <Injects {...props} />
      <div className="disenador-columnas">
        <section className="tarjeta">
          <h2>Roles configurados</h2>
          <p className="texto-suave">Selecciona un rol para asignar tareas e injects.</p>
          <ul className="roles-configurados">
            {d.roles.map((codigo) => {
              const total = d.tareas.filter((t) => t.rol_codigo === codigo).length
              const participante = nombreParticipante(codigo)
              return (
                <li key={codigo}>
                  <button
                    type="button"
                    className={codigo === rol ? 'rol-item seleccionado' : 'rol-item'}
                    aria-pressed={codigo === rol}
                    onClick={() => setRolActivo(codigo)}
                  >
                    <strong>{nombreRol(roles, codigo)}</strong>
                    <span className={participante ? '' : 'texto-peligro'}>
                      {participante
                        ? `${participante} — participante asignado`
                        : 'Sin participante'}
                    </span>
                    <span>{total} tarea(s) asignada(s)</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
        <TareasDelRol key={rol} rol={rol} {...props} />
      </div>
    </>
  )
}

function Injects({ d, cambiar }: PropsPaso) {
  const [abierto, setAbierto] = useState(false)

  const cambiarInject = (id: string, cambios: Partial<SesionDiseno['injects'][0]>) =>
    cambiar((a) => ({
      ...a,
      injects: a.injects.map((i) => (i.id === id ? { ...i, ...cambios } : i)),
    }))

  const mover = (indice: number, delta: number) =>
    cambiar((a) => {
      const lista = [...a.injects]
      const destino = indice + delta
      if (destino < 0 || destino >= lista.length) return a
      ;[lista[indice], lista[destino]] = [lista[destino], lista[indice]]
      return { ...a, injects: lista }
    })

  // Las tareas del inject quitado quedan "sin inject" para reubicarlas.
  const quitar = (id: string) =>
    cambiar((a) => ({
      ...a,
      injects: a.injects.filter((i) => i.id !== id),
      tareas: a.tareas.map((t) => (t.inject_id === id ? { ...t, inject_id: null } : t)),
    }))

  const agregar = () => {
    setAbierto(true)
    cambiar((a) => ({
      ...a,
      injects: [
        ...a.injects,
        { id: nuevoId(), titulo: '', descripcion: '', minuto_sugerido: null },
      ],
    }))
  }

  return (
    <section className="tarjeta">
      <div className="titulo-seccion">
        <h2>Injects de la sesión ({d.injects.length})</h2>
        <div className="acciones">
          <button
            type="button"
            className="boton boton-texto"
            aria-expanded={abierto}
            onClick={() => setAbierto(!abierto)}
          >
            {abierto ? 'Ocultar' : 'Editar injects'}
          </button>
          <button type="button" className="boton" onClick={agregar}>
            + Agregar inject
          </button>
        </div>
      </div>
      {!abierto && (
        <ol className="injects-compactos">
          {d.injects.map((i) => (
            <li key={i.id}>{i.titulo || <em>Sin título</em>}</li>
          ))}
        </ol>
      )}
      {abierto &&
        d.injects.map((i, indice) => (
          <fieldset key={i.id} className="bloque">
            <legend>Inject {indice + 1}</legend>
            <div className="fila-campos">
              <label className="campo campo-ancho">
                <span>Título</span>
                <input
                  required
                  minLength={3}
                  maxLength={150}
                  value={i.titulo}
                  onChange={(e) => cambiarInject(i.id, { titulo: e.target.value })}
                />
              </label>
              <label className="campo campo-corto">
                <span>Minuto</span>
                <input
                  type="number"
                  min={0}
                  max={600}
                  value={i.minuto_sugerido ?? ''}
                  onChange={(e) =>
                    cambiarInject(i.id, {
                      minuto_sugerido: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                />
              </label>
            </div>
            <label className="campo">
              <span>Narrativa del inject</span>
              <textarea
                required
                minLength={10}
                rows={2}
                value={i.descripcion}
                onChange={(e) => cambiarInject(i.id, { descripcion: e.target.value })}
              />
            </label>
            <div className="acciones-bloque">
              <button
                type="button"
                className="boton boton-texto"
                disabled={indice === 0}
                onClick={() => mover(indice, -1)}
              >
                ↑ Subir
              </button>
              <button
                type="button"
                className="boton boton-texto"
                disabled={indice === d.injects.length - 1}
                onClick={() => mover(indice, 1)}
              >
                ↓ Bajar
              </button>
              <button
                type="button"
                className="boton boton-texto texto-peligro"
                onClick={() => quitar(i.id)}
              >
                Quitar
              </button>
            </div>
          </fieldset>
        ))}
    </section>
  )
}

function TareasDelRol({ rol, d, cambiar, roles }: PropsPaso & { rol: string }) {
  const [editando, setEditando] = useState<string | null>(null)
  const numeroInject = (id: string | null) => d.injects.findIndex((i) => i.id === id)
  const tareas = d.tareas
    .filter((t) => t.rol_codigo === rol)
    .sort((a, b) => {
      // Las tareas sin inject van al final.
      const na = numeroInject(a.inject_id)
      const nb = numeroInject(b.inject_id)
      return (na < 0 ? 999 : na) - (nb < 0 ? 999 : nb)
    })

  const cambiarTarea = (id: string, cambios: Partial<TareaSesion>) =>
    cambiar((a) => ({
      ...a,
      tareas: a.tareas.map((t) => (t.id === id ? { ...t, ...cambios } : t)),
    }))

  const agregar = () => {
    // Por defecto, el primer inject en el que este rol todavía no tiene tarea.
    const libre =
      d.injects.find((i) => !tareas.some((t) => t.inject_id === i.id)) ?? d.injects[0]
    const nueva = tareaNueva(rol, libre?.id ?? null)
    cambiar((a) => ({ ...a, tareas: [...a.tareas, nueva] }))
    setEditando(nueva.id)
  }

  return (
    <section className="tarjeta">
      <h2>{nombreRol(roles, rol)} — Tareas asignadas</h2>
      {tareas.length === 0 && (
        <p className="texto-suave">Este rol todavía no tiene tareas.</p>
      )}
      {tareas.map((t) => {
        const n = numeroInject(t.inject_id)
        return (
          <article key={t.id} className={tareaCompleta(t) ? 'tarea' : 'tarea incompleta'}>
            <div className="tarea-cabecera">
              <span className={`badge inject-badge inject-${n < 0 ? 'ninguno' : n % 3}`}>
                {n < 0 ? 'Sin inject' : `Inject ${n + 1}`}
              </span>
              <button
                type="button"
                className="boton boton-texto"
                aria-expanded={editando === t.id}
                onClick={() => setEditando(editando === t.id ? null : t.id)}
              >
                {editando === t.id ? 'Listo' : 'Editar'}
              </button>
            </div>
            {editando === t.id ? (
              <EditorTarea
                t={t}
                d={d}
                cambiar={(cambios) => cambiarTarea(t.id, cambios)}
                quitar={() =>
                  cambiar((a) => ({ ...a, tareas: a.tareas.filter((x) => x.id !== t.id) }))
                }
              />
            ) : (
              <>
                <p className="tarea-enunciado">
                  {t.enunciado || <em>Sin enunciado</em>}
                </p>
                <p className="texto-suave">Tipo: {ETIQUETA_TIPO_TAREA[t.tipo]}</p>
              </>
            )}
          </article>
        )
      })}
      <button
        type="button"
        className="boton boton-agregar"
        disabled={d.injects.length === 0}
        onClick={agregar}
      >
        + Agregar tarea al inject
      </button>
    </section>
  )
}

function EditorTarea({
  t,
  d,
  cambiar,
  quitar,
}: {
  t: TareaSesion
  d: SesionDiseno
  cambiar: (cambios: Partial<TareaSesion>) => void
  quitar: () => void
}) {
  const cambiarOpcion = (indice: number, cambios: Partial<TareaSesion['opciones'][0]>) =>
    cambiar({
      opciones: t.opciones.map((o, i) => (i === indice ? { ...o, ...cambios } : o)),
    })

  return (
    <div className="editor-tarea">
      <div className="fila-campos">
        <label className="campo">
          <span>Inject</span>
          <select
            value={t.inject_id ?? ''}
            onChange={(e) => cambiar({ inject_id: e.target.value || null })}
          >
            <option value="">Sin inject</option>
            {d.injects.map((i, n) => (
              <option key={i.id} value={i.id}>
                Inject {n + 1}: {i.titulo}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Tipo de respuesta</span>
          <select
            value={t.tipo}
            onChange={(e) => {
              const tipo = e.target.value as TipoTarea
              cambiar({
                tipo,
                opciones:
                  tipo === 'seleccion_multiple' && t.opciones.length === 0
                    ? [
                        { texto: '', correcta: true },
                        { texto: '', correcta: false },
                      ]
                    : t.opciones,
              })
            }}
          >
            <option value="texto_libre">{ETIQUETA_TIPO_TAREA.texto_libre}</option>
            <option value="seleccion_multiple">
              {ETIQUETA_TIPO_TAREA.seleccion_multiple}
            </option>
          </select>
        </label>
      </div>
      <label className="campo">
        <span>Pregunta o tarea</span>
        <textarea
          required
          minLength={10}
          rows={2}
          value={t.enunciado}
          onChange={(e) => cambiar({ enunciado: e.target.value })}
        />
      </label>

      {t.tipo === 'seleccion_multiple' ? (
        <fieldset className="bloque">
          <legend>Opciones (marca las correctas)</legend>
          {t.opciones.map((o, i) => (
            <div key={i} className="fila-opcion">
              <input
                type="checkbox"
                aria-label={`Opción ${i + 1} correcta`}
                checked={o.correcta}
                onChange={(e) => cambiarOpcion(i, { correcta: e.target.checked })}
              />
              <input
                aria-label={`Texto de la opción ${i + 1}`}
                maxLength={300}
                value={o.texto}
                onChange={(e) => cambiarOpcion(i, { texto: e.target.value })}
              />
              <button
                type="button"
                className="boton boton-texto texto-peligro"
                aria-label={`Quitar opción ${i + 1}`}
                onClick={() => cambiar({ opciones: t.opciones.filter((_, x) => x !== i) })}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            className="boton boton-texto"
            disabled={t.opciones.length >= 8}
            onClick={() =>
              cambiar({ opciones: [...t.opciones, { texto: '', correcta: false }] })
            }
          >
            + Agregar opción
          </button>
        </fieldset>
      ) : (
        <label className="campo">
          <span>Criterios de evaluación (uno por línea)</span>
          <textarea
            rows={3}
            value={t.criterios.join('\n')}
            onChange={(e) => cambiar({ criterios: e.target.value.split('\n') })}
          />
        </label>
      )}

      <div className="fila-campos">
        <label className="campo">
          <span>Dificultad</span>
          <select
            value={t.dificultad}
            onChange={(e) => cambiar({ dificultad: e.target.value as Nivel })}
          >
            {NIVELES.map((n) => (
              <option key={n} value={n}>
                {ETIQUETA_NIVEL[n]}
              </option>
            ))}
          </select>
        </label>
        <label className="campo campo-corto">
          <span>Minutos</span>
          <input
            type="number"
            min={0.5}
            max={60}
            step={0.5}
            value={t.tiempo_limite_segundos / 60}
            onChange={(e) =>
              cambiar({ tiempo_limite_segundos: Math.round(Number(e.target.value) * 60) })
            }
          />
        </label>
      </div>
      <div className="acciones-bloque">
        <button type="button" className="boton boton-texto texto-peligro" onClick={quitar}>
          Quitar tarea
        </button>
      </div>
    </div>
  )
}
