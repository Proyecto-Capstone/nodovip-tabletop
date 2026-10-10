// PB-03: crear y editar escenarios base (solo Administrador).

import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  actualizarEscenario,
  crearEscenario,
  rutas,
  type EscenarioDetalle,
  type EscenarioEntrada,
  type Nivel,
  type RolEjercicio,
  type TipoEscenario,
} from '../api/escenarios'
import { useRol } from '../auth/rolContext'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { ETIQUETA_NIVEL, NIVELES, nombreRol } from '../lib/etiquetas'
import { useGet } from '../lib/useGet'

const MIN_INJECTS = 3

interface InjectForm {
  clave: string
  id?: string
  titulo: string
  descripcion: string
  minuto: string
}

interface TareaForm {
  clave: string
  id?: string
  enunciado: string
  rol_codigo: string
  dificultad: Nivel
  criterios: string
  puntaje: string
  tiempoMin: string
  respuesta: string
}

interface Formulario {
  nombre: string
  tipo_codigo: string
  descripcion: string
  nivel: Nivel
  roles: string[]
  injects: InjectForm[]
  tareas: TareaForm[]
}

const nuevaClave = () => crypto.randomUUID()

const injectVacio = (): InjectForm => ({
  clave: nuevaClave(),
  titulo: '',
  descripcion: '',
  minuto: '',
})

const tareaVacia = (rol = ''): TareaForm => ({
  clave: nuevaClave(),
  enunciado: '',
  rol_codigo: rol,
  dificultad: 'medio',
  criterios: '',
  puntaje: '10',
  tiempoMin: '5',
  respuesta: '',
})

function desdeDetalle(e: EscenarioDetalle): Formulario {
  return {
    nombre: e.nombre,
    tipo_codigo: e.tipo_codigo,
    descripcion: e.descripcion,
    nivel: e.nivel,
    roles: e.roles,
    injects: e.injects.map((i) => ({
      clave: i.id,
      id: i.id,
      titulo: i.titulo,
      descripcion: i.descripcion,
      minuto: i.minuto_sugerido === null ? '' : String(i.minuto_sugerido),
    })),
    tareas: e.tareas.map((t) => ({
      clave: t.id,
      id: t.id,
      enunciado: t.enunciado,
      rol_codigo: t.rol_codigo,
      dificultad: t.dificultad,
      criterios: t.criterios.join('\n'),
      puntaje: String(t.puntaje_maximo),
      tiempoMin: String(Math.round(t.tiempo_limite_segundos / 60)),
      respuesta: t.respuesta_esperada ?? '',
    })),
  }
}

function aEntrada(f: Formulario): EscenarioEntrada {
  return {
    nombre: f.nombre.trim(),
    tipo_codigo: f.tipo_codigo,
    descripcion: f.descripcion.trim(),
    nivel: f.nivel,
    roles: f.roles,
    injects: f.injects.map((i) => ({
      ...(i.id ? { id: i.id } : {}),
      titulo: i.titulo.trim(),
      descripcion: i.descripcion.trim(),
      minuto_sugerido: i.minuto === '' ? null : Number(i.minuto),
    })),
    tareas: f.tareas.map((t) => ({
      ...(t.id ? { id: t.id } : {}),
      enunciado: t.enunciado.trim(),
      rol_codigo: t.rol_codigo,
      dificultad: t.dificultad,
      criterios: t.criterios
        .split('\n')
        .map((c) => c.trim())
        .filter(Boolean),
      puntaje_maximo: Number(t.puntaje),
      tiempo_limite_segundos: Math.round(Number(t.tiempoMin) * 60),
      respuesta_esperada: t.respuesta.trim() || null,
    })),
  }
}

export function EscenarioFormPage() {
  const { id } = useParams()
  const { rol, esAdministrador } = useRol()
  const tipos = useGet<TipoEscenario[]>(esAdministrador ? rutas.tipos : null, rol)
  const roles = useGet<RolEjercicio[]>(esAdministrador ? rutas.roles : null, rol)
  const existente = useGet<EscenarioDetalle>(
    esAdministrador && id ? rutas.escenario(id) : null,
    rol,
  )

  if (!esAdministrador) return <SinPermiso />
  const errores = tipos.errores ?? roles.errores ?? existente.errores
  if (errores) return <Errores errores={errores} />
  if (!tipos.datos || !roles.datos || (id && !existente.datos)) return <Cargando />

  return (
    <FormularioEscenario
      key={id ?? 'nuevo'}
      id={id}
      inicial={existente.datos ? desdeDetalle(existente.datos) : undefined}
      tipos={tipos.datos}
      roles={roles.datos}
    />
  )
}

function FormularioEscenario({
  id,
  inicial,
  tipos,
  roles,
}: {
  id?: string
  inicial?: Formulario
  tipos: TipoEscenario[]
  roles: RolEjercicio[]
}) {
  const navigate = useNavigate()
  const [f, setF] = useState<Formulario>(
    inicial ?? {
      nombre: '',
      tipo_codigo: '',
      descripcion: '',
      nivel: 'medio',
      roles: [],
      injects: [injectVacio(), injectVacio(), injectVacio()],
      tareas: [],
    },
  )
  const [errores, setErrores] = useState<string[]>()
  const [guardando, setGuardando] = useState(false)

  const cambiar = (cambios: Partial<Formulario>) => setF((a) => ({ ...a, ...cambios }))

  const elegirTipo = (codigo: string) => {
    const tipo = tipos.find((t) => t.codigo === codigo)
    setF((a) => ({
      ...a,
      tipo_codigo: codigo,
      // Si todavía no eligió roles, se proponen los del tipo (Tabla 6).
      roles: a.roles.length === 0 && tipo ? tipo.roles_sugeridos : a.roles,
      nivel: a.tipo_codigo === '' && tipo ? tipo.nivel_complejidad : a.nivel,
    }))
  }

  const alternarRol = (codigo: string) =>
    setF((a) => ({
      ...a,
      roles: a.roles.includes(codigo)
        ? a.roles.filter((r) => r !== codigo)
        : [...a.roles, codigo],
    }))

  const cambiarInject = (clave: string, cambios: Partial<InjectForm>) =>
    setF((a) => ({
      ...a,
      injects: a.injects.map((i) => (i.clave === clave ? { ...i, ...cambios } : i)),
    }))

  const moverInject = (indice: number, delta: number) =>
    setF((a) => {
      const lista = [...a.injects]
      const destino = indice + delta
      if (destino < 0 || destino >= lista.length) return a
      ;[lista[indice], lista[destino]] = [lista[destino], lista[indice]]
      return { ...a, injects: lista }
    })

  const cambiarTarea = (clave: string, cambios: Partial<TareaForm>) =>
    setF((a) => ({
      ...a,
      tareas: a.tareas.map((t) => (t.clave === clave ? { ...t, ...cambios } : t)),
    }))

  // Reglas de RF-04, calculadas en vivo para guiar al administrador.
  const rolesSinTareas = f.roles.filter(
    (r) => !f.tareas.some((t) => t.rol_codigo === r),
  )
  const tareasHuerfanas = f.tareas.filter((t) => !f.roles.includes(t.rol_codigo))
  const requisitos = [
    {
      ok: f.injects.length >= MIN_INJECTS,
      texto: `Al menos ${MIN_INJECTS} injects (tiene ${f.injects.length})`,
    },
    { ok: f.roles.length > 0, texto: 'Al menos un rol involucrado' },
    {
      ok: f.roles.length > 0 && rolesSinTareas.length === 0,
      texto: rolesSinTareas.length
        ? `Tareas para cada rol (faltan: ${rolesSinTareas
            .map((r) => nombreRol(roles, r))
            .join(', ')})`
        : 'Tareas para cada rol',
    },
  ]

  const guardar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (tareasHuerfanas.length) {
      setErrores(['Hay tareas sin rol o con un rol que ya no está en el escenario'])
      return
    }
    setGuardando(true)
    setErrores(undefined)
    try {
      const datos = aEntrada(f)
      const guardado = id
        ? await actualizarEscenario(id, datos)
        : await crearEscenario(datos)
      navigate(`/escenarios/${guardado.id}`)
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={guardar}>
      <Link to={id ? `/escenarios/${id}` : '/escenarios'} className="volver">
        ← {id ? 'Volver al escenario' : 'Biblioteca de escenarios'}
      </Link>
      <div className="encabezado">
        <div>
          <h1>{id ? 'Editar escenario' : 'Nuevo escenario base'}</h1>
          <p className="texto-suave">
            Se guarda como borrador. Publícalo desde su ficha cuando cumpla los
            requisitos.
          </p>
        </div>
      </div>

      <Errores errores={errores} />

      <div className="formulario-columnas">
        <div>
          <section className="tarjeta">
            <h2>1. Datos generales</h2>
            <label className="campo">
              <span>Nombre</span>
              <input
                required
                minLength={3}
                maxLength={150}
                value={f.nombre}
                onChange={(e) => cambiar({ nombre: e.target.value })}
              />
            </label>
            <div className="fila-campos">
              <label className="campo">
                <span>Tipo de incidente</span>
                <select
                  required
                  value={f.tipo_codigo}
                  onChange={(e) => elegirTipo(e.target.value)}
                >
                  <option value="">Elegir…</option>
                  {tipos.map((t) => (
                    <option key={t.codigo} value={t.codigo}>
                      {t.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label className="campo">
                <span>Complejidad</span>
                <select
                  value={f.nivel}
                  onChange={(e) => cambiar({ nivel: e.target.value as Nivel })}
                >
                  {NIVELES.map((n) => (
                    <option key={n} value={n}>
                      {ETIQUETA_NIVEL[n]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="campo">
              <span>Descripción del incidente</span>
              <textarea
                required
                minLength={20}
                maxLength={5000}
                rows={4}
                value={f.descripcion}
                onChange={(e) => cambiar({ descripcion: e.target.value })}
              />
            </label>
          </section>

          <section className="tarjeta">
            <h2>2. Roles involucrados</h2>
            <div className="opciones-roles">
              {roles.map((r) => (
                <label key={r.codigo} className="opcion">
                  <input
                    type="checkbox"
                    checked={f.roles.includes(r.codigo)}
                    onChange={() => alternarRol(r.codigo)}
                  />
                  {r.nombre}
                </label>
              ))}
            </div>
          </section>

          <section className="tarjeta">
            <div className="titulo-seccion">
              <h2>3. Injects</h2>
              <button
                type="button"
                className="boton"
                onClick={() => cambiar({ injects: [...f.injects, injectVacio()] })}
              >
                + Agregar inject
              </button>
            </div>
            {f.injects.map((i, indice) => (
              <fieldset key={i.clave} className="bloque">
                <legend>Inject {indice + 1}</legend>
                <div className="fila-campos">
                  <label className="campo campo-ancho">
                    <span>Título</span>
                    <input
                      required
                      minLength={3}
                      maxLength={150}
                      value={i.titulo}
                      onChange={(e) => cambiarInject(i.clave, { titulo: e.target.value })}
                    />
                  </label>
                  <label className="campo campo-corto">
                    <span>Minuto</span>
                    <input
                      type="number"
                      min={0}
                      max={600}
                      value={i.minuto}
                      onChange={(e) => cambiarInject(i.clave, { minuto: e.target.value })}
                    />
                  </label>
                </div>
                <label className="campo">
                  <span>Descripción</span>
                  <textarea
                    required
                    minLength={10}
                    rows={2}
                    value={i.descripcion}
                    onChange={(e) =>
                      cambiarInject(i.clave, { descripcion: e.target.value })
                    }
                  />
                </label>
                <div className="acciones-bloque">
                  <button
                    type="button"
                    className="boton boton-texto"
                    disabled={indice === 0}
                    onClick={() => moverInject(indice, -1)}
                  >
                    ↑ Subir
                  </button>
                  <button
                    type="button"
                    className="boton boton-texto"
                    disabled={indice === f.injects.length - 1}
                    onClick={() => moverInject(indice, 1)}
                  >
                    ↓ Bajar
                  </button>
                  <button
                    type="button"
                    className="boton boton-texto texto-peligro"
                    onClick={() =>
                      cambiar({ injects: f.injects.filter((x) => x.clave !== i.clave) })
                    }
                  >
                    Quitar
                  </button>
                </div>
              </fieldset>
            ))}
          </section>

          <section className="tarjeta">
            <div className="titulo-seccion">
              <h2>4. Tareas y preguntas por rol</h2>
              <button
                type="button"
                className="boton"
                disabled={f.roles.length === 0}
                title={f.roles.length === 0 ? 'Primero elige los roles' : ''}
                onClick={() =>
                  cambiar({
                    tareas: [...f.tareas, tareaVacia(rolesSinTareas[0] ?? f.roles[0])],
                  })
                }
              >
                + Agregar tarea
              </button>
            </div>
            {f.tareas.length === 0 && (
              <p className="texto-suave">Agrega al menos una tarea para cada rol.</p>
            )}
            {f.tareas.map((t, indice) => (
              <fieldset key={t.clave} className="bloque">
                <legend>Tarea {indice + 1}</legend>
                <div className="fila-campos">
                  <label className="campo">
                    <span>Rol</span>
                    <select
                      required
                      value={t.rol_codigo}
                      onChange={(e) =>
                        cambiarTarea(t.clave, { rol_codigo: e.target.value })
                      }
                    >
                      <option value="">Elegir…</option>
                      {f.roles.map((r) => (
                        <option key={r} value={r}>
                          {nombreRol(roles, r)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="campo">
                    <span>Dificultad</span>
                    <select
                      value={t.dificultad}
                      onChange={(e) =>
                        cambiarTarea(t.clave, { dificultad: e.target.value as Nivel })
                      }
                    >
                      {NIVELES.map((n) => (
                        <option key={n} value={n}>
                          {ETIQUETA_NIVEL[n]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="campo campo-corto">
                    <span>Puntaje</span>
                    <input
                      type="number"
                      required
                      min={1}
                      max={100}
                      value={t.puntaje}
                      onChange={(e) => cambiarTarea(t.clave, { puntaje: e.target.value })}
                    />
                  </label>
                  <label className="campo campo-corto">
                    <span>Minutos</span>
                    <input
                      type="number"
                      required
                      min={0.5}
                      max={60}
                      step={0.5}
                      value={t.tiempoMin}
                      onChange={(e) =>
                        cambiarTarea(t.clave, { tiempoMin: e.target.value })
                      }
                    />
                  </label>
                </div>
                <label className="campo">
                  <span>Pregunta o tarea</span>
                  <textarea
                    required
                    minLength={10}
                    rows={2}
                    value={t.enunciado}
                    onChange={(e) => cambiarTarea(t.clave, { enunciado: e.target.value })}
                  />
                </label>
                <label className="campo">
                  <span>Criterios de evaluación (uno por línea)</span>
                  <textarea
                    required
                    rows={3}
                    value={t.criterios}
                    onChange={(e) => cambiarTarea(t.clave, { criterios: e.target.value })}
                  />
                </label>
                <label className="campo">
                  <span>Respuesta esperada (opcional)</span>
                  <textarea
                    rows={2}
                    value={t.respuesta}
                    onChange={(e) => cambiarTarea(t.clave, { respuesta: e.target.value })}
                  />
                </label>
                <div className="acciones-bloque">
                  <button
                    type="button"
                    className="boton boton-texto texto-peligro"
                    onClick={() =>
                      cambiar({ tareas: f.tareas.filter((x) => x.clave !== t.clave) })
                    }
                  >
                    Quitar
                  </button>
                </div>
              </fieldset>
            ))}
          </section>
        </div>

        <aside className="tarjeta resumen-lateral">
          <h2>Requisitos para publicar</h2>
          <ul className="requisitos">
            {requisitos.map((r) => (
              <li key={r.texto} className={r.ok ? 'ok' : 'pendiente'}>
                <span aria-hidden="true">{r.ok ? '✓' : '○'}</span> {r.texto}
              </li>
            ))}
          </ul>
          {tareasHuerfanas.length > 0 && (
            <p className="texto-peligro">
              {tareasHuerfanas.length} tarea(s) sin rol válido.
            </p>
          )}
          <button
            type="submit"
            className="boton boton-primario boton-bloque"
            disabled={guardando}
          >
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        </aside>
      </div>
    </form>
  )
}
