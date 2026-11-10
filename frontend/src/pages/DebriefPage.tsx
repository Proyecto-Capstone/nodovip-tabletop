// PC-45: debrief (hot wash) de una sesión finalizada. El moderador registra
// fortalezas, aspectos a mejorar y un plan de acción con responsable, plazo y
// prioridad. Se guarda como borrador; al completarlo pasa al reporte de brechas.
// Analista y Administrador lo ven en solo lectura.

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  completarDebrief,
  ETIQUETA_PRIORIDAD,
  formatoPlazo,
  guardarDebrief,
  reabrirDebrief,
  rutasDebrief,
  type AccionMejora,
  type Debrief,
  type DebriefEntrada,
  type PrioridadAccion,
} from '../api/debrief'
import { rutasReportes, type Recomendacion, type Reporte } from '../api/reportes'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { Lecciones } from '../components/Lecciones'
import { useGet, useGetVigente } from '../lib/useGet'

interface AccionForm extends AccionMejora {
  clave: string
}

interface Formulario {
  fortalezas: string[]
  mejoras: string[]
  acciones: AccionForm[]
}

const nuevaClave = () => crypto.randomUUID()

const accionVacia = (cambios: Partial<AccionMejora> = {}): AccionForm => ({
  clave: nuevaClave(),
  descripcion: '',
  prioridad: 'media',
  rol_codigo: null,
  plazo: null,
  ...cambios,
})

function desdeDebrief(d: Debrief): Formulario {
  return {
    // Siempre al menos un campo para escribir.
    fortalezas: d.fortalezas.length ? d.fortalezas : [''],
    mejoras: d.mejoras.length ? d.mejoras : [''],
    acciones: d.acciones.map((a) =>
      accionVacia({
        descripcion: a.descripcion,
        prioridad: a.prioridad,
        rol_codigo: a.rol_codigo,
        plazo: a.plazo,
      }),
    ),
  }
}

function aEntrada(f: Formulario): DebriefEntrada {
  return {
    fortalezas: f.fortalezas,
    mejoras: f.mejoras,
    acciones: f.acciones.map((a) => ({
      descripcion: a.descripcion,
      prioridad: a.prioridad,
      rol_codigo: a.rol_codigo,
      plazo: a.plazo,
    })),
  }
}

const ETIQUETA_ESTADO: Record<Debrief['estado'], string> = {
  sin_iniciar: 'Sin iniciar',
  borrador: 'Borrador',
  completado: 'Completado',
}

export function DebriefPage() {
  const { id = '' } = useParams()
  const { rol } = useSesion()
  // Vigente: al recargar tras guardar, el formulario sigue en pantalla.
  const debrief = useGetVigente<Debrief>(rutasDebrief.debrief(id), rol)
  // El reporte da contexto: brechas y recomendaciones para armar el plan.
  const reporte = useGet<Reporte>(rutasReportes.reporte(id), rol)

  if (debrief.status === 404) {
    return (
      <div className="alerta alerta-aviso">
        Debrief no disponible: la sesión no existe o todavía no ha finalizado.{' '}
        <Link to="/sesiones">Ver mis tabletops</Link>
      </div>
    )
  }
  if (debrief.errores) return <Errores errores={debrief.errores} />
  if (!debrief.datos) return <Cargando />
  return (
    <Contenido
      // El formulario conserva lo escrito: tras guardar coincide con lo guardado.
      d={debrief.datos}
      reporte={reporte.datos}
      recargar={debrief.recargar}
    />
  )
}

function Contenido({
  d,
  reporte,
  recargar,
}: {
  d: Debrief
  reporte?: Reporte
  recargar: () => void
}) {
  const [f, setF] = useState<Formulario>(() => desdeDebrief(d))
  const [cambios, setCambios] = useState(false)
  const [enviando, setEnviando] = useState<'guardar' | 'completar' | 'reabrir' | null>(null)
  const [errores, setErrores] = useState<string[]>()
  const [aviso, setAviso] = useState<string>()

  const editable = d.puede_editar && d.estado !== 'completado'
  const cambiar = (nuevo: Partial<Formulario>) => {
    setF((a) => ({ ...a, ...nuevo }))
    setCambios(true)
    setAviso(undefined)
  }

  const ejecutar = async (accion: 'guardar' | 'completar' | 'reabrir', mensaje: string) => {
    setEnviando(accion)
    setErrores(undefined)
    setAviso(undefined)
    try {
      if (accion !== 'reabrir') await guardarDebrief(d.sesion_id, aEntrada(f))
      if (accion === 'completar') await completarDebrief(d.sesion_id)
      if (accion === 'reabrir') await reabrirDebrief(d.sesion_id)
      setCambios(false)
      setAviso(mensaje)
      recargar()
    } catch (e) {
      setErrores(e instanceof ApiError ? e.errores : ['Error de conexión'])
      // Lo guardado antes del error (el borrador) también cuenta.
      if (accion === 'completar') recargar()
    } finally {
      setEnviando(null)
    }
  }

  const agregarRecomendacion = (r: Recomendacion) => {
    const rol = d.roles.find((x) => x.nombre === r.rol_nombre)
    cambiar({
      acciones: [
        ...f.acciones,
        accionVacia({
          descripcion: r.texto,
          prioridad: r.prioridad,
          rol_codigo: rol?.codigo ?? null,
        }),
      ],
    })
  }

  return (
    <>
      <Link
        to={d.puede_editar ? '/sesiones' : rutasReportes.reporte(d.sesion_id)}
        className="volver"
      >
        ← {d.puede_editar ? 'Mis tabletops' : 'Reporte'}
      </Link>
      <div className="encabezado">
        <div>
          <h1>Debrief: {d.sesion_nombre}</h1>
          <p className="texto-suave">
            <span className={`badge debrief-${d.estado}`}>{ETIQUETA_ESTADO[d.estado]}</span>
            {d.cliente && ` · Cliente: ${d.cliente}`}
            {d.completado_en &&
              ` · Completado el ${new Date(d.completado_en).toLocaleString('es-EC', {
                dateStyle: 'medium',
                timeStyle: 'short',
              })}`}
          </p>
        </div>
        <div className="acciones-fila">
          <Link className="boton boton-secundario" to={rutasReportes.reporte(d.sesion_id)}>
            Ver reporte
          </Link>
          {d.puede_editar && d.estado === 'completado' && (
            <button
              type="button"
              className="boton boton-secundario"
              disabled={enviando !== null}
              onClick={() => ejecutar('reabrir', 'El debrief volvió a borrador.')}
            >
              {enviando === 'reabrir' ? 'Reabriendo…' : 'Reabrir para editar'}
            </button>
          )}
        </div>
      </div>

      {editable && (
        <p className="parrafo texto-suave debrief-intro">
          Reúne al equipo justo después del ejercicio (hot wash): ¿qué funcionó?, ¿qué hay que
          mejorar? y ¿qué haremos al respecto? Al completarlo, las lecciones y el plan de acción se
          agregan al reporte de brechas.
        </p>
      )}
      <Errores errores={errores} />
      {aviso && (
        <div className="alerta alerta-exito" role="status">
          {aviso}
        </div>
      )}

      {!editable ? (
        <SoloLectura d={d} />
      ) : (
        <div className="debrief-layout">
          <div className="debrief-formulario">
            <section className="tarjeta" aria-labelledby="titulo-fortalezas">
              <h2 id="titulo-fortalezas">Fortalezas</h2>
              <p className="texto-suave texto-chico">
                Lo que el equipo hizo bien y conviene mantener.
              </p>
              <ListaEditable
                nombre="Fortaleza"
                valores={f.fortalezas}
                ejemplo="Ej.: El CISO escaló el incidente a la dirección en menos de 5 minutos."
                onChange={(fortalezas) => cambiar({ fortalezas })}
              />
            </section>

            <section className="tarjeta" aria-labelledby="titulo-mejoras">
              <h2 id="titulo-mejoras">Aspectos a mejorar</h2>
              <p className="texto-suave texto-chico">
                Brechas de proceso, coordinación o conocimiento que salieron a la luz.
              </p>
              <ListaEditable
                nombre="Aspecto a mejorar"
                valores={f.mejoras}
                ejemplo="Ej.: Nadie verificó la integridad de la copia fuera de línea."
                onChange={(mejoras) => cambiar({ mejoras })}
              />
            </section>

            <section className="tarjeta" aria-labelledby="titulo-plan">
              <div className="titulo-seccion">
                <h2 id="titulo-plan">Plan de acción</h2>
                <button
                  type="button"
                  className="boton boton-secundario"
                  onClick={() => cambiar({ acciones: [...f.acciones, accionVacia()] })}
                >
                  + Agregar acción
                </button>
              </div>
              {f.acciones.length === 0 && (
                <p className="texto-suave">
                  Agrega al menos una acción con responsable y plazo, o súmala desde las
                  recomendaciones del reporte.
                </p>
              )}
              {f.acciones.map((a, i) => (
                <EditorAccion
                  key={a.clave}
                  numero={i + 1}
                  accion={a}
                  roles={d.roles}
                  onChange={(cambiada) =>
                    cambiar({
                      acciones: f.acciones.map((x) => (x.clave === a.clave ? cambiada : x)),
                    })
                  }
                  onQuitar={() =>
                    cambiar({
                      acciones: f.acciones.filter((x) => x.clave !== a.clave),
                    })
                  }
                />
              ))}
            </section>

            <div className="debrief-barra">
              <span className="texto-suave texto-chico" role="status">
                {cambios ? '● Cambios sin guardar' : d.actualizado_en ? 'Todo guardado' : ''}
              </span>
              <div className="acciones-fila">
                <button
                  type="button"
                  className="boton boton-secundario"
                  disabled={enviando !== null}
                  onClick={() => ejecutar('guardar', 'Borrador guardado.')}
                >
                  {enviando === 'guardar' ? 'Guardando…' : 'Guardar borrador'}
                </button>
                <button
                  type="button"
                  className="boton boton-primario"
                  disabled={enviando !== null}
                  onClick={() =>
                    ejecutar(
                      'completar',
                      'Debrief completado. El reporte PDF se está regenerando con las lecciones.',
                    )
                  }
                >
                  {enviando === 'completar' ? 'Completando…' : 'Completar debrief'}
                </button>
              </div>
            </div>
          </div>

          <aside className="tarjeta debrief-contexto" aria-labelledby="titulo-hallazgos">
            <h2 id="titulo-hallazgos">Hallazgos del ejercicio</h2>
            {!reporte ? (
              <p className="texto-suave">Cargando el reporte…</p>
            ) : (
              <>
                <p className="texto-suave texto-chico">
                  Puntaje global <strong>{reporte.porcentaje_total} %</strong> ·{' '}
                  {reporte.brechas.length} brechas detectadas
                </p>
                <h3>Recomendaciones</h3>
                <ul className="debrief-recomendaciones">
                  {reporte.recomendaciones.map((r, i) => (
                    <li key={i}>
                      <span className={`badge severidad-${r.prioridad}`}>
                        {ETIQUETA_PRIORIDAD[r.prioridad]}
                      </span>{' '}
                      <strong>{r.rol_nombre}:</strong> {r.texto}
                      <button
                        type="button"
                        className="boton boton-texto"
                        onClick={() => agregarRecomendacion(r)}
                      >
                        + Agregar al plan
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </aside>
        </div>
      )}
    </>
  )
}

function SoloLectura({ d }: { d: Debrief }) {
  if (d.estado === 'sin_iniciar' || (!d.puede_editar && d.estado === 'borrador')) {
    return (
      <p className="tarjeta vacio">
        {d.estado === 'sin_iniciar'
          ? 'El moderador todavía no registró el debrief de esta sesión.'
          : 'El moderador está preparando el debrief: aparecerá aquí cuando lo complete.'}
      </p>
    )
  }
  return (
    <section className="tarjeta" aria-label="Lecciones aprendidas">
      <Lecciones fortalezas={d.fortalezas} mejoras={d.mejoras} acciones={d.acciones} />
    </section>
  )
}

function ListaEditable({
  nombre,
  valores,
  ejemplo,
  onChange,
}: {
  nombre: string
  valores: string[]
  ejemplo: string
  onChange: (valores: string[]) => void
}) {
  return (
    <div className="lista-editable">
      {valores.map((v, i) => (
        <div key={i} className="lista-editable-fila">
          <textarea
            aria-label={`${nombre} ${i + 1}`}
            rows={2}
            maxLength={1000}
            placeholder={i === 0 ? ejemplo : ''}
            value={v}
            onChange={(e) => onChange(valores.map((x, j) => (j === i ? e.target.value : x)))}
          />
          <button
            type="button"
            className="boton boton-texto texto-peligro"
            aria-label={`Quitar ${nombre.toLowerCase()} ${i + 1}`}
            onClick={() => onChange(valores.filter((_, j) => j !== i))}
          >
            Quitar
          </button>
        </div>
      ))}
      <button
        type="button"
        className="boton boton-texto"
        onClick={() => onChange([...valores, ''])}
      >
        + Agregar {nombre.toLowerCase()}
      </button>
    </div>
  )
}

function EditorAccion({
  numero,
  accion,
  roles,
  onChange,
  onQuitar,
}: {
  numero: number
  accion: AccionForm
  roles: Debrief['roles']
  onChange: (a: AccionForm) => void
  onQuitar: () => void
}) {
  const cambiar = (c: Partial<AccionMejora>) => onChange({ ...accion, ...c })
  return (
    <fieldset className="bloque editor-accion">
      <legend>Acción {numero}</legend>
      <label className="campo">
        <span>Qué se hará</span>
        <textarea
          rows={2}
          maxLength={500}
          value={accion.descripcion}
          onChange={(e) => cambiar({ descripcion: e.target.value })}
        />
      </label>
      <div className="fila-campos">
        <label className="campo">
          <span>Responsable</span>
          <select
            value={accion.rol_codigo ?? ''}
            onChange={(e) => cambiar({ rol_codigo: e.target.value || null })}
          >
            <option value="">Toda la organización</option>
            {roles.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo campo-corto">
          <span>Prioridad</span>
          <select
            value={accion.prioridad}
            onChange={(e) => cambiar({ prioridad: e.target.value as PrioridadAccion })}
          >
            {Object.entries(ETIQUETA_PRIORIDAD).map(([codigo, nombre]) => (
              <option key={codigo} value={codigo}>
                {nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Plazo</span>
          <input
            type="date"
            value={accion.plazo ?? ''}
            onChange={(e) => cambiar({ plazo: e.target.value || null })}
          />
        </label>
      </div>
      <div className="acciones-bloque">
        {accion.plazo && (
          <span className="texto-suave texto-chico">Vence: {formatoPlazo(accion.plazo)}</span>
        )}
        <button type="button" className="boton boton-texto texto-peligro" onClick={onQuitar}>
          Quitar acción
        </button>
      </div>
    </fieldset>
  )
}
