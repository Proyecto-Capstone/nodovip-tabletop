// PB-03: crear y editar escenarios base (solo Administrador).

import { useState, type FormEvent, type ReactNode } from 'react'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  Circle,
  FileText,
  ListChecks,
  Plus,
  Save,
  Trash2,
  Users,
  Zap,
} from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  actualizarEscenario,
  crearEscenario,
  rutas,
  type EscenarioDetalle,
  type EscenarioEntrada,
  type Evidencia,
  type Nivel,
  type RolEjercicio,
  type TipoEscenario,
} from '../api/escenarios'
import { useSesion } from '../auth/sesionContext'
import { Anillo } from '../components/Anillo'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { EditorOpciones } from '../components/EditorOpciones'
import { EditorEvidencia } from '../components/Evidencia'
import { ETIQUETA_NIVEL, NIVELES, nombreRol } from '../lib/etiquetas'
import { useGet } from '../lib/useGet'
import type { Opcion, TipoTarea } from '../api/sesiones'
import { ETIQUETA_TIPO_TAREA, opcionesIniciales } from './disenador/comun'

const MIN_INJECTS = 3

interface InjectForm {
  clave: string
  id?: string
  titulo: string
  descripcion: string
  minuto: string
  evidencia: Evidencia | null
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
  tipo: TipoTarea
  opciones: Opcion[]
  /** Clave del inject en el que se pregunta ('' = repartir en orden). */
  injectClave: string
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
  evidencia: null,
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
  tipo: 'texto_libre',
  opciones: [],
  injectClave: '',
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
      evidencia: i.evidencia,
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
      tipo: t.tipo,
      opciones: t.opciones,
      injectClave: e.injects.find((i) => i.orden === t.inject_orden)?.id ?? '',
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
      evidencia: i.evidencia
        ? {
            ...i.evidencia,
            origen: i.evidencia.origen.trim(),
            asunto: i.evidencia.asunto.trim(),
            contenido: i.evidencia.contenido.trim(),
          }
        : null,
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
      tipo: t.tipo,
      opciones:
        t.tipo === 'seleccion_multiple'
          ? t.opciones.map((o) => ({ ...o, texto: o.texto.trim() }))
          : [],
      // El inject se guarda por su posición actual (los injects se pueden reordenar).
      inject_orden: t.injectClave
        ? f.injects.findIndex((i) => i.clave === t.injectClave) + 1 || null
        : null,
    })),
  }
}

export function EscenarioFormPage() {
  const { id } = useParams()
  const { rol, puedeGestionarEscenarios } = useSesion()
  const tipos = useGet<TipoEscenario[]>(puedeGestionarEscenarios ? rutas.tipos : null, rol)
  const roles = useGet<RolEjercicio[]>(puedeGestionarEscenarios ? rutas.roles : null, rol)
  const existente = useGet<EscenarioDetalle>(
    puedeGestionarEscenarios && id ? rutas.escenario(id) : null,
    rol,
  )

  if (!puedeGestionarEscenarios) return <SinPermiso />
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
      roles: a.roles.includes(codigo) ? a.roles.filter((r) => r !== codigo) : [...a.roles, codigo],
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
  const rolesSinTareas = f.roles.filter((r) => !f.tareas.some((t) => t.rol_codigo === r))
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
      const guardado = id ? await actualizarEscenario(id, datos) : await crearEscenario(datos)
      navigate(`/escenarios/${guardado.id}`)
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } finally {
      setGuardando(false)
    }
  }

  const cumplidos = requisitos.filter((r) => r.ok).length
  const avance = Math.round((cumplidos / requisitos.length) * 100)
  const secciones = [
    { id: 'seccion-datos', texto: 'Datos generales', listo: Boolean(f.nombre && f.tipo_codigo) },
    { id: 'seccion-roles', texto: 'Roles', listo: f.roles.length > 0 },
    { id: 'seccion-injects', texto: 'Injects', listo: f.injects.length >= MIN_INJECTS },
    {
      id: 'seccion-tareas',
      texto: 'Tareas por rol',
      listo: f.roles.length > 0 && rolesSinTareas.length === 0,
    },
  ]

  return (
    <form onSubmit={guardar} className="formulario-escenario">
      <Link to={id ? `/escenarios/${id}` : '/escenarios'} className="volver">
        <ArrowLeft size={16} aria-hidden="true" />
        {id ? 'Volver al escenario' : 'Biblioteca de escenarios'}
      </Link>
      <div className="encabezado">
        <div>
          <h1>{id ? 'Editar escenario' : 'Nuevo escenario base'}</h1>
          <p className="texto-suave">
            Se guarda como borrador. Publícalo desde su ficha cuando cumpla los requisitos.
          </p>
        </div>
      </div>

      <Errores errores={errores} />

      <div className="formulario-columnas">
        <div className="formulario-secciones">
          <section
            className="tarjeta seccion-formulario"
            id="seccion-datos"
            aria-labelledby="titulo-datos"
          >
            <CabeceraSeccion
              numero={1}
              icono={<FileText />}
              id="titulo-datos"
              titulo="Datos generales"
              descripcion="Nombre, tipo de incidente, complejidad y la historia que se presenta."
            />
            <label className="campo">
              <span>Nombre</span>
              <input
                required
                minLength={3}
                maxLength={150}
                placeholder="Ej.: Ransomware en servidores de archivos"
                value={f.nombre}
                onChange={(e) => cambiar({ nombre: e.target.value })}
              />
            </label>
            <div className="fila-campos">
              <label className="campo">
                <span>Tipo de incidente</span>
                <select required value={f.tipo_codigo} onChange={(e) => elegirTipo(e.target.value)}>
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
                placeholder="Contexto que verán los participantes al iniciar el ejercicio."
                value={f.descripcion}
                onChange={(e) => cambiar({ descripcion: e.target.value })}
              />
            </label>
          </section>

          <section
            className="tarjeta seccion-formulario"
            id="seccion-roles"
            aria-labelledby="titulo-roles"
          >
            <CabeceraSeccion
              numero={2}
              icono={<Users />}
              id="titulo-roles"
              titulo="Roles involucrados"
              descripcion="Al elegir el tipo de incidente se proponen sus roles sugeridos."
              extra={
                <span className="contador" aria-label={`${f.roles.length} roles elegidos`}>
                  {f.roles.length}
                </span>
              }
            />
            <div className="fichas-roles">
              {roles.map((r) => {
                const marcado = f.roles.includes(r.codigo)
                return (
                  <label key={r.codigo} className={`ficha-rol${marcado ? ' marcada' : ''}`}>
                    <input
                      type="checkbox"
                      checked={marcado}
                      onChange={() => alternarRol(r.codigo)}
                    />
                    <span className="ficha-rol-marca" aria-hidden="true">
                      {marcado && <Check />}
                    </span>
                    {r.nombre}
                  </label>
                )
              })}
            </div>
          </section>

          <section
            className="tarjeta seccion-formulario"
            id="seccion-injects"
            aria-labelledby="titulo-injects"
          >
            <CabeceraSeccion
              numero={3}
              icono={<Zap />}
              id="titulo-injects"
              titulo="Injects"
              descripcion={`Eventos que el moderador lanza durante el ejercicio (mínimo ${MIN_INJECTS}).`}
              extra={
                <button
                  type="button"
                  className="boton boton-secundario"
                  onClick={() => cambiar({ injects: [...f.injects, injectVacio()] })}
                >
                  <Plus size={16} aria-hidden="true" />
                  Agregar inject
                </button>
              }
            />
            <ol className="lista-bloques">
              {f.injects.map((i, indice) => (
                <li key={i.clave}>
                  <fieldset className="bloque bloque-numerado">
                    <legend className="solo-lector">Inject {indice + 1}</legend>
                    <div className="bloque-cabecera">
                      <span className="bloque-numero" aria-hidden="true">
                        {indice + 1}
                      </span>
                      <span className="bloque-titulo">
                        <span className="bloque-tipo">Inject {indice + 1}</span>
                        {i.titulo || <em>Sin título</em>}
                      </span>
                      <span className="bloque-acciones">
                        <button
                          type="button"
                          className="boton-icono"
                          disabled={indice === 0}
                          aria-label={`Subir inject ${indice + 1}`}
                          title="Subir"
                          onClick={() => moverInject(indice, -1)}
                        >
                          <ArrowUp aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          className="boton-icono"
                          disabled={indice === f.injects.length - 1}
                          aria-label={`Bajar inject ${indice + 1}`}
                          title="Bajar"
                          onClick={() => moverInject(indice, 1)}
                        >
                          <ArrowDown aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          className="boton-icono boton-icono-peligro"
                          aria-label={`Quitar inject ${indice + 1}`}
                          title="Quitar"
                          onClick={() =>
                            cambiar({ injects: f.injects.filter((x) => x.clave !== i.clave) })
                          }
                        >
                          <Trash2 aria-hidden="true" />
                        </button>
                      </span>
                    </div>
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
                        onChange={(e) => cambiarInject(i.clave, { descripcion: e.target.value })}
                      />
                    </label>
                    <EditorEvidencia
                      valor={i.evidencia}
                      onChange={(evidencia) => cambiarInject(i.clave, { evidencia })}
                    />
                  </fieldset>
                </li>
              ))}
            </ol>
          </section>

          <section
            className="tarjeta seccion-formulario"
            id="seccion-tareas"
            aria-labelledby="titulo-tareas"
          >
            <CabeceraSeccion
              numero={4}
              icono={<ListChecks />}
              id="titulo-tareas"
              titulo="Tareas y preguntas por rol"
              descripcion="Cada rol necesita al menos una tarea. Se evalúa por criterios u opciones."
              extra={
                <button
                  type="button"
                  className="boton boton-secundario"
                  disabled={f.roles.length === 0}
                  title={f.roles.length === 0 ? 'Primero elige los roles' : ''}
                  onClick={() =>
                    cambiar({
                      tareas: [...f.tareas, tareaVacia(rolesSinTareas[0] ?? f.roles[0])],
                    })
                  }
                >
                  <Plus size={16} aria-hidden="true" />
                  Agregar tarea
                </button>
              }
            />
            {f.tareas.length === 0 && (
              <div className="vacio vacio-compacto">
                {f.roles.length === 0
                  ? 'Primero elige los roles involucrados.'
                  : 'Agrega al menos una tarea para cada rol.'}
              </div>
            )}
            <ol className="lista-bloques">
              {f.tareas.map((t, indice) => (
                <li key={t.clave}>
                  <fieldset className="bloque bloque-numerado">
                    <legend className="solo-lector">Tarea {indice + 1}</legend>
                    <div className="bloque-cabecera">
                      <span className="bloque-numero" aria-hidden="true">
                        {indice + 1}
                      </span>
                      <span className="bloque-titulo">
                        <span className="bloque-tipo">Tarea {indice + 1}</span>
                        {t.rol_codigo ? nombreRol(roles, t.rol_codigo) : <em>Sin rol</em>}
                        <span className="bloque-detalle">
                          {ETIQUETA_TIPO_TAREA[t.tipo]} · {t.puntaje || 0} pts
                        </span>
                      </span>
                      <span className="bloque-acciones">
                        <button
                          type="button"
                          className="boton-icono boton-icono-peligro"
                          aria-label={`Quitar tarea ${indice + 1}`}
                          title="Quitar"
                          onClick={() =>
                            cambiar({ tareas: f.tareas.filter((x) => x.clave !== t.clave) })
                          }
                        >
                          <Trash2 aria-hidden="true" />
                        </button>
                      </span>
                    </div>
                    <div className="fila-campos">
                      <label className="campo">
                        <span>Rol</span>
                        <select
                          required
                          value={t.rol_codigo}
                          onChange={(e) => cambiarTarea(t.clave, { rol_codigo: e.target.value })}
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
                          onChange={(e) => cambiarTarea(t.clave, { tiempoMin: e.target.value })}
                        />
                      </label>
                    </div>
                    <div className="fila-campos">
                      <label className="campo">
                        <span>Se pregunta en</span>
                        <select
                          value={t.injectClave}
                          onChange={(e) => cambiarTarea(t.clave, { injectClave: e.target.value })}
                        >
                          <option value="">Repartir en orden</option>
                          {f.injects.map((i, n) => (
                            <option key={i.clave} value={i.clave}>
                              Inject {n + 1}
                              {i.titulo ? ` · ${i.titulo}` : ''}
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
                            cambiarTarea(t.clave, {
                              tipo,
                              opciones:
                                tipo === 'seleccion_multiple' && t.opciones.length === 0
                                  ? opcionesIniciales()
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
                        onChange={(e) => cambiarTarea(t.clave, { enunciado: e.target.value })}
                      />
                    </label>
                    {t.tipo === 'seleccion_multiple' ? (
                      <EditorOpciones
                        opciones={t.opciones}
                        onChange={(opciones) => cambiarTarea(t.clave, { opciones })}
                      />
                    ) : (
                      <label className="campo">
                        <span>Criterios de evaluación (uno por línea)</span>
                        <textarea
                          required
                          rows={3}
                          value={t.criterios}
                          onChange={(e) => cambiarTarea(t.clave, { criterios: e.target.value })}
                        />
                      </label>
                    )}
                    <label className="campo">
                      <span>Respuesta esperada (opcional)</span>
                      <textarea
                        rows={2}
                        value={t.respuesta}
                        onChange={(e) => cambiarTarea(t.clave, { respuesta: e.target.value })}
                      />
                    </label>
                  </fieldset>
                </li>
              ))}
            </ol>
          </section>
        </div>

        <aside className="tarjeta resumen-lateral" aria-labelledby="titulo-requisitos">
          <div className="resumen-avance">
            <Anillo porcentaje={avance} />
            <div>
              <h2 id="titulo-requisitos">Requisitos para publicar</h2>
              <p className="texto-suave">
                {cumplidos} de {requisitos.length} cumplidos
              </p>
            </div>
          </div>
          <ul className="requisitos">
            {requisitos.map((r) => (
              <li key={r.texto} className={r.ok ? 'ok' : 'pendiente'}>
                {r.ok ? (
                  <Check size={14} aria-hidden="true" />
                ) : (
                  <Circle size={14} aria-hidden="true" />
                )}{' '}
                {r.texto}
              </li>
            ))}
          </ul>
          {tareasHuerfanas.length > 0 && (
            <p className="texto-peligro">{tareasHuerfanas.length} tarea(s) sin rol válido.</p>
          )}

          <dl className="resumen-conteo">
            <div>
              <dt>Roles</dt>
              <dd>{f.roles.length}</dd>
            </div>
            <div>
              <dt>Injects</dt>
              <dd>{f.injects.length}</dd>
            </div>
            <div>
              <dt>Tareas</dt>
              <dd>{f.tareas.length}</dd>
            </div>
          </dl>

          <nav className="indice-formulario" aria-label="Secciones del formulario">
            {secciones.map((sec, n) => (
              <a key={sec.id} href={`#${sec.id}`} className={sec.listo ? 'listo' : undefined}>
                <span className="indice-numero" aria-hidden="true">
                  {sec.listo ? <Check /> : n + 1}
                </span>
                {sec.texto}
                {sec.listo && <span className="solo-lector"> (completo)</span>}
              </a>
            ))}
          </nav>

          <button
            type="submit"
            className="boton boton-primario boton-destacado boton-bloque"
            disabled={guardando}
          >
            <Save size={17} aria-hidden="true" />
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
          <p className="texto-suave resumen-nota">Se guarda como borrador.</p>
        </aside>
      </div>
    </form>
  )
}

function CabeceraSeccion({
  numero,
  icono,
  id,
  titulo,
  descripcion,
  extra,
}: {
  numero: number
  icono: ReactNode
  id: string
  titulo: string
  descripcion: string
  extra?: ReactNode
}) {
  return (
    <div className="seccion-cabecera">
      <span className="seccion-icono" aria-hidden="true">
        {icono}
        <span className="seccion-numero">{numero}</span>
      </span>
      <div className="seccion-textos">
        <h2 id={id}>{titulo}</h2>
        <p className="texto-suave">{descripcion}</p>
      </div>
      {extra && <div className="seccion-extra">{extra}</div>}
    </div>
  )
}
