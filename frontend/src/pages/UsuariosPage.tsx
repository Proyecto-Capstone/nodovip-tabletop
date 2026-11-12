// PB-02: panel de administración de usuarios y roles (solo Administrador).
// Los usuarios se agrupan por categoría de rol y cada tarjeta permite cambiar
// el rol en línea (con confirmación: los permisos cambian al instante) y las
// acciones rápidas de seguridad.

import { useMemo, useState, type FormEvent, type ReactNode } from 'react'
import {
  Check,
  Circle,
  Eye,
  History,
  KeyRound,
  Pencil,
  Power,
  Search,
  ShieldCheck,
  Trash2,
  UserPlus,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { ApiError, type RolSistema } from '../api/client'
import {
  activarUsuario,
  actualizarUsuario,
  crearUsuario,
  desactivarUsuario,
  eliminarUsuario,
  restablecerContrasena,
  rutaUsuarios,
  type Usuario,
} from '../api/usuarios'
import { ROLES_SISTEMA, nombreRolSistema, useSesion } from '../auth/sesionContext'
import { useConfirmar } from '../components/confirmacionContext'
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { Indicador } from '../components/Indicador'
import { contrasenaValida, reglasContrasena } from '../lib/contrasena'
import { useDebounce, useGet } from '../lib/useGet'

type Panel =
  | { modo: 'crear' }
  | { modo: 'editar'; usuario: Usuario }
  | { modo: 'contrasena'; usuario: Usuario }

interface Categoria {
  clave: string
  titulo: string
  descripcion: string
  roles: RolSistema[]
  icono: ReactNode
}

const CATEGORIAS: Categoria[] = [
  {
    clave: 'administracion',
    titulo: 'Administradores',
    descripcion: 'Usuarios, escenarios y auditoría',
    roles: ['administrador'],
    icono: <ShieldCheck />,
  },
  {
    clave: 'moderacion',
    titulo: 'Moderación y análisis',
    descripcion: 'Moderadores, analistas y observadores',
    roles: ['moderador', 'analista', 'observador'],
    icono: <Eye />,
  },
  {
    clave: 'participacion',
    titulo: 'Participantes',
    descripcion: 'Responden en los ejercicios',
    roles: ['participante'],
    icono: <Users />,
  },
]

const formatoFecha = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString('es-EC', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      })
    : '—'

function mensajes(error: unknown) {
  return error instanceof ApiError ? error.errores : ['Error de conexión']
}

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean)
  return (
    (partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')
  ).toUpperCase()
}

export function UsuariosPage() {
  const { rol, usuario: yo, puedeGestionarUsuarios } = useSesion()
  const confirmar = useConfirmar()
  const [texto, setTexto] = useState('')
  const [rolFiltro, setRolFiltro] = useState('')
  const [estado, setEstado] = useState('')
  const [panel, setPanel] = useState<Panel | null>(null)
  const [aviso, setAviso] = useState<string>()
  const [errores, setErrores] = useState<string[]>()
  const [ocupado, setOcupado] = useState<string | null>(null)
  const q = useDebounce(texto.trim())

  const usuarios = useGet<Usuario[]>(
    puedeGestionarUsuarios
      ? rutaUsuarios({ q, rol: rolFiltro, activo: estado || undefined })
      : null,
    rol,
  )
  // Indicadores: siempre sobre todos los usuarios, no sobre lo filtrado.
  const todos = useGet<Usuario[]>(puedeGestionarUsuarios ? rutaUsuarios({}) : null, rol)

  const porCategoria = useMemo(
    () =>
      CATEGORIAS.map((c) => ({
        ...c,
        usuarios: (usuarios.datos ?? []).filter((u) => c.roles.includes(u.rol)),
      })),
    [usuarios.datos],
  )

  if (!puedeGestionarUsuarios) return <SinPermiso />

  const recargar = () => {
    usuarios.recargar()
    todos.recargar()
  }

  const terminar = (mensaje: string) => {
    setPanel(null)
    setErrores(undefined)
    setAviso(mensaje)
    recargar()
  }

  const abrirPanel = (p: Panel) => {
    setAviso(undefined)
    setErrores(undefined)
    setPanel(p)
    requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'smooth' }))
  }

  const cambiarRol = async (u: Usuario, nuevo: RolSistema) => {
    if (nuevo === u.rol) return
    setAviso(undefined)
    setErrores(undefined)
    if (
      !(await confirmar({
        titulo: `¿Cambiar el rol de ${u.nombre}?`,
        cuerpo: `Pasará de ${nombreRolSistema(u.rol)} a ${nombreRolSistema(nuevo)}. Sus permisos cambian de inmediato, también en la sesión que tenga abierta.`,
        textoConfirmar: 'Cambiar rol',
      }))
    ) {
      return
    }
    setOcupado(u.id)
    try {
      await actualizarUsuario(u.id, { nombre: u.nombre, correo: u.correo, rol: nuevo })
      terminar(`${u.nombre} ahora es ${nombreRolSistema(nuevo)}.`)
    } catch (error) {
      setErrores(mensajes(error))
    } finally {
      setOcupado(null)
    }
  }

  const cambiarEstado = async (u: Usuario) => {
    setAviso(undefined)
    setErrores(undefined)
    if (
      u.activo &&
      !(await confirmar({
        titulo: `¿Desactivar a ${u.nombre}?`,
        cuerpo: 'No podrá ingresar al sistema.',
        textoConfirmar: 'Desactivar',
      }))
    ) {
      return
    }
    setOcupado(u.id)
    try {
      if (u.activo) await desactivarUsuario(u.id)
      else await activarUsuario(u.id)
      terminar(`${u.nombre} ${u.activo ? 'desactivado' : 'activado'}.`)
    } catch (error) {
      setErrores(mensajes(error))
    } finally {
      setOcupado(null)
    }
  }

  const eliminar = async (u: Usuario) => {
    setAviso(undefined)
    setErrores(undefined)
    if (
      !(await confirmar({
        titulo: `¿Eliminar definitivamente a ${u.nombre}?`,
        cuerpo: `Correo ${u.correo}. Esta acción no se puede deshacer.`,
        textoConfirmar: 'Eliminar',
      }))
    ) {
      return
    }
    try {
      await eliminarUsuario(u.id)
      terminar(`${u.nombre} eliminado definitivamente.`)
    } catch (error) {
      setErrores(mensajes(error))
    }
  }

  const lista = todos.datos ?? []
  const contar = (roles: RolSistema[]) => {
    const deRol = lista.filter((u) => roles.includes(u.rol))
    return {
      activos: deRol.filter((u) => u.activo).length,
      inactivos: deRol.filter((u) => !u.activo).length,
    }
  }
  const resumen = [
    {
      tono: 'azul' as const,
      icono: <ShieldCheck />,
      etiqueta: 'Administradores',
      ...contar(['administrador']),
    },
    { tono: 'verde' as const, icono: <Users />, etiqueta: 'Moderadores', ...contar(['moderador']) },
    {
      tono: 'naranja' as const,
      icono: <Eye />,
      etiqueta: 'Analistas y observadores',
      ...contar(['analista', 'observador']),
    },
    {
      tono: 'gris' as const,
      icono: <Users />,
      etiqueta: 'Participantes',
      ...contar(['participante']),
    },
  ]

  return (
    <div className="usuarios">
      <div className="encabezado">
        <div>
          <h1>Gestión de usuarios y control de acceso</h1>
          <p className="texto-suave">
            Usuarios agrupados por categoría de rol. Cambia el rol desde cada tarjeta y controla
            quién puede ingresar (RBAC).
          </p>
        </div>
        <button
          type="button"
          className="boton boton-primario boton-destacado"
          onClick={() => abrirPanel({ modo: 'crear' })}
        >
          <UserPlus size={17} aria-hidden="true" />
          Nuevo usuario
        </button>
      </div>

      {todos.datos && (
        <section className="indicadores" aria-label="Usuarios por rol">
          {resumen.map((r) => (
            <Indicador
              key={r.etiqueta}
              tono={r.tono}
              icono={r.icono}
              etiqueta={r.etiqueta}
              valor={r.activos}
              detalle={r.inactivos ? `activos · ${r.inactivos} desactivados` : 'activos'}
            />
          ))}
        </section>
      )}

      {aviso && (
        <div className="alerta alerta-exito" role="status">
          {aviso}
        </div>
      )}
      <Errores errores={errores} />

      {panel?.modo === 'crear' || panel?.modo === 'editar' ? (
        <FormularioUsuario
          key={panel.modo === 'editar' ? panel.usuario.id : 'nuevo'}
          usuario={panel.modo === 'editar' ? panel.usuario : undefined}
          onCancelar={() => setPanel(null)}
          onGuardado={(u, nuevo) =>
            terminar(nuevo ? `Usuario ${u.correo} creado.` : `Cambios de ${u.nombre} guardados.`)
          }
        />
      ) : null}

      {panel?.modo === 'contrasena' && (
        <FormularioContrasena
          key={panel.usuario.id}
          usuario={panel.usuario}
          onCancelar={() => setPanel(null)}
          onGuardado={(u) => terminar(`Contraseña de ${u.nombre} restablecida.`)}
        />
      )}

      <section className="filtros-biblioteca filtros-usuarios" aria-label="Filtros">
        <label className="campo campo-busqueda">
          <span>Buscar</span>
          <span className="campo-icono">
            <Search aria-hidden="true" />
            <input
              type="search"
              placeholder="Nombre o correo…"
              value={texto}
              maxLength={100}
              onChange={(e) => setTexto(e.target.value)}
            />
          </span>
        </label>
        <label className="campo">
          <span>Rol</span>
          <select value={rolFiltro} onChange={(e) => setRolFiltro(e.target.value)}>
            <option value="">Todos</option>
            {ROLES_SISTEMA.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Estado</span>
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
        </label>
      </section>

      <Errores errores={usuarios.errores} />
      {usuarios.cargando && !usuarios.datos && <Cargando />}
      {usuarios.datos?.length === 0 && (
        <div className="tarjeta vacio">No hay usuarios con esos filtros.</div>
      )}

      {usuarios.datos && usuarios.datos.length > 0 && (
        <div className="columnas-usuarios">
          {porCategoria.map((c) => (
            <section
              key={c.clave}
              className={`columna-usuarios columna-${c.clave}`}
              aria-labelledby={`titulo-${c.clave}`}
            >
              <header className="columna-usuarios-cabecera">
                <span className="columna-usuarios-icono" aria-hidden="true">
                  {c.icono}
                </span>
                <div>
                  <h2 id={`titulo-${c.clave}`}>{c.titulo}</h2>
                  <p className="texto-suave">{c.descripcion}</p>
                </div>
                <span className="contador">{c.usuarios.length}</span>
              </header>
              {c.usuarios.length === 0 ? (
                <p className="columna-usuarios-vacia">Sin usuarios en esta categoría.</p>
              ) : (
                <ul className="lista-usuarios">
                  {c.usuarios.map((u) => (
                    <li key={u.id}>
                      <TarjetaUsuario
                        usuario={u}
                        esYo={u.id === yo?.id}
                        ocupado={ocupado === u.id}
                        onRol={(nuevo) => cambiarRol(u, nuevo)}
                        onEditar={() => abrirPanel({ modo: 'editar', usuario: u })}
                        onContrasena={() => abrirPanel({ modo: 'contrasena', usuario: u })}
                        onEstado={() => cambiarEstado(u)}
                        onEliminar={() => eliminar(u)}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  )
}

function TarjetaUsuario({
  usuario: u,
  esYo,
  ocupado,
  onRol,
  onEditar,
  onContrasena,
  onEstado,
  onEliminar,
}: {
  usuario: Usuario
  esYo: boolean
  ocupado: boolean
  onRol: (rol: RolSistema) => void
  onEditar: () => void
  onContrasena: () => void
  onEstado: () => void
  onEliminar: () => void
}) {
  return (
    <article
      className={`tarjeta-usuario rol-${u.rol}${u.activo ? '' : ' inactivo'}`}
      aria-label={u.nombre}
      aria-busy={ocupado}
    >
      <div className="tarjeta-usuario-cabecera">
        <span className="avatar avatar-usuario" aria-hidden="true">
          {iniciales(u.nombre)}
        </span>
        <div className="tarjeta-usuario-datos">
          <strong>
            {u.nombre}
            {esYo && <span className="etiqueta-tu">Tú</span>}
          </strong>
          <span className="texto-suave">{u.correo}</span>
        </div>
        <span className={`badge ${u.activo ? 'estado-activo' : 'estado-inactivo'}`}>
          {u.activo ? 'Activo' : 'Inactivo'}
        </span>
      </div>
      <div className="tarjeta-usuario-pie">
        <label className="selector-rol">
          <span className="solo-lector">Rol de {u.nombre}</span>
          <select
            value={u.rol}
            disabled={esYo || ocupado}
            title={esYo ? 'No puedes cambiar tu propio rol' : 'Cambiar rol'}
            onChange={(e) => onRol(e.target.value as RolSistema)}
          >
            {ROLES_SISTEMA.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.nombre}
              </option>
            ))}
          </select>
        </label>
        <div className="tarjeta-usuario-acciones">
          <button
            type="button"
            className="boton-icono"
            aria-label="Editar"
            title="Editar nombre, correo y rol"
            onClick={onEditar}
          >
            <Pencil aria-hidden="true" />
          </button>
          <button
            type="button"
            className="boton-icono boton-icono-clave"
            aria-label="Contraseña"
            title="Restablecer contraseña"
            onClick={onContrasena}
          >
            <KeyRound aria-hidden="true" />
          </button>
          <Link
            className="boton-icono"
            to={`/accesos?usuario=${u.id}`}
            aria-label="Accesos"
            title="Ver historial de accesos"
          >
            <History aria-hidden="true" />
          </Link>
          {!esYo && (
            <button
              type="button"
              className={`boton-icono ${u.activo ? 'boton-icono-peligro' : 'boton-icono-exito'}`}
              aria-label={u.activo ? 'Desactivar' : 'Activar'}
              title={u.activo ? 'Desactivar la cuenta' : 'Activar la cuenta'}
              disabled={ocupado}
              onClick={onEstado}
            >
              <Power aria-hidden="true" />
            </button>
          )}
          {!u.activo && (
            <button
              type="button"
              className="boton-icono boton-icono-peligro"
              aria-label="Eliminar"
              title="Eliminar definitivamente"
              onClick={onEliminar}
            >
              <Trash2 aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
      <p className="tarjeta-usuario-fecha">Creado el {formatoFecha(u.creado_en)}</p>
    </article>
  )
}

function ReglasContrasena({ valor }: { valor: string }) {
  return (
    <ul className="requisitos requisitos-compactos" aria-label="Requisitos de la contraseña">
      {reglasContrasena(valor).map((r) => (
        <li key={r.texto} className={r.ok ? 'ok' : 'pendiente'}>
          {r.ok ? <Check size={14} aria-hidden="true" /> : <Circle size={14} aria-hidden="true" />}{' '}
          {r.texto}
        </li>
      ))}
    </ul>
  )
}

function FormularioUsuario({
  usuario,
  onCancelar,
  onGuardado,
}: {
  usuario?: Usuario
  onCancelar: () => void
  onGuardado: (u: Usuario, nuevo: boolean) => void
}) {
  const [nombre, setNombre] = useState(usuario?.nombre ?? '')
  const [correo, setCorreo] = useState(usuario?.correo ?? '')
  const [rol, setRol] = useState<RolSistema>(usuario?.rol ?? 'participante')
  const [contrasena, setContrasena] = useState('')
  const [errores, setErrores] = useState<string[]>()
  const [guardando, setGuardando] = useState(false)
  const nuevo = !usuario

  const guardar = async (e: FormEvent) => {
    e.preventDefault()
    if (nuevo && !contrasenaValida(contrasena)) {
      setErrores(['La contraseña no cumple los requisitos'])
      return
    }
    setGuardando(true)
    setErrores(undefined)
    try {
      const guardado = usuario
        ? await actualizarUsuario(usuario.id, { nombre, correo, rol })
        : await crearUsuario({ nombre, correo, contrasena, rol })
      onGuardado(guardado, nuevo)
    } catch (error) {
      setErrores(mensajes(error))
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form className="tarjeta panel-formulario panel-usuario" onSubmit={guardar}>
      <h2>{nuevo ? 'Nuevo usuario' : `Editar a ${usuario.nombre}`}</h2>
      <Errores errores={errores} />
      <div className="fila-campos">
        <label className="campo">
          <span>Nombre completo</span>
          <input
            required
            minLength={3}
            maxLength={150}
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </label>
        <label className="campo">
          <span>Correo</span>
          <input
            type="email"
            required
            maxLength={255}
            autoComplete="off"
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
          />
        </label>
        <label className="campo">
          <span>Rol</span>
          <select value={rol} onChange={(e) => setRol(e.target.value as RolSistema)}>
            {ROLES_SISTEMA.map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      {nuevo && (
        <div className="fila-campos">
          <label className="campo">
            <span>Contraseña inicial</span>
            <input
              type="password"
              required
              autoComplete="new-password"
              value={contrasena}
              onChange={(e) => setContrasena(e.target.value)}
            />
          </label>
          <ReglasContrasena valor={contrasena} />
        </div>
      )}
      <div className="acciones">
        <button type="submit" className="boton boton-primario" disabled={guardando}>
          {guardando ? 'Guardando…' : nuevo ? 'Crear usuario' : 'Guardar cambios'}
        </button>
        <button type="button" className="boton" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

function FormularioContrasena({
  usuario,
  onCancelar,
  onGuardado,
}: {
  usuario: Usuario
  onCancelar: () => void
  onGuardado: (u: Usuario) => void
}) {
  const [contrasena, setContrasena] = useState('')
  const [errores, setErrores] = useState<string[]>()
  const [guardando, setGuardando] = useState(false)

  const guardar = async (e: FormEvent) => {
    e.preventDefault()
    if (!contrasenaValida(contrasena)) {
      setErrores(['La contraseña no cumple los requisitos'])
      return
    }
    setGuardando(true)
    try {
      onGuardado(await restablecerContrasena(usuario.id, contrasena))
    } catch (error) {
      setErrores(mensajes(error))
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form className="tarjeta panel-formulario panel-usuario" onSubmit={guardar}>
      <h2>Restablecer contraseña de {usuario.nombre}</h2>
      <Errores errores={errores} />
      <div className="fila-campos">
        <label className="campo">
          <span>Nueva contraseña</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
          />
        </label>
        <ReglasContrasena valor={contrasena} />
      </div>
      <div className="acciones">
        <button type="submit" className="boton boton-primario" disabled={guardando}>
          {guardando ? 'Guardando…' : 'Restablecer'}
        </button>
        <button type="button" className="boton" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}
