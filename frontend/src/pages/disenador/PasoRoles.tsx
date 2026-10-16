// Paso 2: roles de la sesión y el participante que asume cada uno (CU-03.2).

import { nombreRol } from '../../lib/etiquetas'
import { participanteDe, type PropsPaso } from './comun'

export function PasoRoles({ d, cambiar, roles, disponibles }: PropsPaso) {
  const alternarRol = (codigo: string) => {
    const activo = d.roles.includes(codigo)
    const tareas = d.tareas.filter((t) => t.rol_codigo === codigo).length
    if (
      activo &&
      tareas > 0 &&
      !confirm(
        `Quitar ${nombreRol(roles, codigo)} también quita sus ${tareas} tarea(s). ¿Continuar?`,
      )
    ) {
      return
    }
    cambiar((a) =>
      activo
        ? {
            ...a,
            roles: a.roles.filter((r) => r !== codigo),
            tareas: a.tareas.filter((t) => t.rol_codigo !== codigo),
            participantes: a.participantes.filter((p) => p.rol_codigo !== codigo),
          }
        : { ...a, roles: [...a.roles, codigo] },
    )
  }

  const asignar = (rol: string, usuario_id: string) =>
    cambiar((a) => ({
      ...a,
      participantes: [
        ...a.participantes.filter((p) => p.rol_codigo !== rol),
        ...(usuario_id ? [{ usuario_id, rol_codigo: rol }] : []),
      ],
    }))

  const usados = new Set(d.participantes.map((p) => p.usuario_id))

  return (
    <section className="tarjeta">
      <h2>Roles y participantes</h2>
      <p className="texto-suave">
        Marca los roles que intervienen y asigna un participante a cada uno. Un
        participante solo puede tener un rol en la sesión.
      </p>
      {disponibles.length === 0 && (
        <div className="alerta alerta-aviso">
          No hay participantes activos. Pide al administrador que cree cuentas con
          el rol Participante.
        </div>
      )}
      <ul className="lista-roles">
        {roles.map((r) => {
          const activo = d.roles.includes(r.codigo)
          const elegido = participanteDe(d, r.codigo)
          return (
            <li key={r.codigo} className={activo ? 'activo' : ''}>
              <label className="opcion">
                <input
                  type="checkbox"
                  checked={activo}
                  onChange={() => alternarRol(r.codigo)}
                />
                {r.nombre}
              </label>
              {activo && (
                <label className="campo">
                  <span className="solo-lector">Participante para {r.nombre}</span>
                  <select
                    value={elegido}
                    onChange={(e) => asignar(r.codigo, e.target.value)}
                  >
                    <option value="">Sin participante asignado</option>
                    {disponibles
                      .filter((u) => u.id === elegido || !usados.has(u.id))
                      .map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.nombre} — {u.correo}
                        </option>
                      ))}
                  </select>
                </label>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
