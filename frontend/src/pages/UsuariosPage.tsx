// PB-02: panel de administración de usuarios y roles (solo Administrador).

import { useState, type FormEvent } from 'react'
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
import { Cargando, Errores, SinPermiso } from '../components/Etiquetas'
import { contrasenaValida, reglasContrasena } from '../lib/contrasena'
import { useDebounce, useGet } from '../lib/useGet'

type Panel =
  | { modo: 'crear' }
  | { modo: 'editar'; usuario: Usuario }
  | { modo: 'contrasena'; usuario: Usuario }

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

export function UsuariosPage() {
  const { rol, puedeGestionarUsuarios } = useSesion()
  const [texto, setTexto] = useState('')
  const [rolFiltro, setRolFiltro] = useState('')
  const [estado, setEstado] = useState('')
  const [panel, setPanel] = useState<Panel | null>(null)
  const [aviso, setAviso] = useState<string>()
  const [errores, setErrores] = useState<string[]>()
  const q = useDebounce(texto.trim())

  const usuarios = useGet<Usuario[]>(
    puedeGestionarUsuarios
      ? rutaUsuarios({ q, rol: rolFiltro, activo: estado || undefined })
      : null,
    rol,
  )

  if (!puedeGestionarUsuarios) return <SinPermiso />

  const terminar = (mensaje: string) => {
    setPanel(null)
    setErrores(undefined)
    setAviso(mensaje)
    usuarios.recargar()
  }

  const cambiarEstado = async (u: Usuario) => {
    setAviso(undefined)
    setErrores(undefined)
    if (u.activo && !confirm(`¿Desactivar a ${u.nombre}? No podrá ingresar al sistema.`)) {
      return
    }
    try {
      if (u.activo) await desactivarUsuario(u.id)
      else await activarUsuario(u.id)
      terminar(`${u.nombre} ${u.activo ? 'desactivado' : 'activado'}.`)
    } catch (error) {
      setErrores(mensajes(error))
    }
  }

  const eliminar = async (u: Usuario) => {
    setAviso(undefined)
    setErrores(undefined)
    if (
      !confirm(
        `¿Eliminar definitivamente a ${u.nombre} (${u.correo})? Esta acción no se puede deshacer.`,
      )
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

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Gestión de usuarios</h1>
          <p className="texto-suave">
            Crea usuarios, asigna su rol y controla quién puede ingresar.
          </p>
        </div>
        <button
          type="button"
          className="boton boton-primario"
          onClick={() => {
            setAviso(undefined)
            setErrores(undefined)
            setPanel({ modo: 'crear' })
          }}
        >
          + Nuevo usuario
        </button>
      </div>

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

      <section className="tarjeta filtros" aria-label="Filtros">
        <label className="campo campo-busqueda">
          <span>Buscar</span>
          <input
            type="search"
            placeholder="Nombre o correo…"
            value={texto}
            maxLength={100}
            onChange={(e) => setTexto(e.target.value)}
          />
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
        <div className="tarjeta tabla-contenedor">
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Creado</th>
                <th>
                  <span className="solo-lector">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {usuarios.datos.map((u) => (
                <tr key={u.id} className={u.activo ? '' : 'fila-inactiva'}>
                  <td>{u.nombre}</td>
                  <td>{u.correo}</td>
                  <td>{nombreRolSistema(u.rol)}</td>
                  <td>
                    <span className={`badge ${u.activo ? 'estado-activo' : 'estado-inactivo'}`}>
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="sin-salto">{formatoFecha(u.creado_en)}</td>
                  <td>
                    <div className="acciones-fila">
                      <button
                        type="button"
                        className="boton boton-texto"
                        onClick={() => {
                          setAviso(undefined)
                          setPanel({ modo: 'editar', usuario: u })
                        }}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="boton boton-texto"
                        onClick={() => {
                          setAviso(undefined)
                          setPanel({ modo: 'contrasena', usuario: u })
                        }}
                      >
                        Contraseña
                      </button>
                      <Link
                        className="boton boton-texto"
                        to={`/accesos?usuario=${u.id}`}
                      >
                        Accesos
                      </Link>
                      <button
                        type="button"
                        className={`boton boton-texto ${u.activo ? 'texto-peligro' : ''}`}
                        onClick={() => cambiarEstado(u)}
                      >
                        {u.activo ? 'Desactivar' : 'Activar'}
                      </button>
                      {!u.activo && (
                        <button
                          type="button"
                          className="boton boton-texto texto-peligro"
                          onClick={() => eliminar(u)}
                        >
                          Eliminar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function ReglasContrasena({ valor }: { valor: string }) {
  return (
    <ul className="requisitos requisitos-compactos" aria-label="Requisitos de la contraseña">
      {reglasContrasena(valor).map((r) => (
        <li key={r.texto} className={r.ok ? 'ok' : 'pendiente'}>
          <span aria-hidden="true">{r.ok ? '✓' : '○'}</span> {r.texto}
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
    <form className="tarjeta panel-formulario" onSubmit={guardar}>
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
    <form className="tarjeta panel-formulario" onSubmit={guardar}>
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
