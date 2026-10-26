// Paso 6: estado de las invitaciones por correo y reenvío (CU-03.6, PB-06).

import type { RolEjercicio } from '../../api/escenarios'
import type { ParticipanteDisponible, SesionDetalle } from '../../api/sesiones'
import { InvitacionBadge } from '../../components/Etiquetas'
import { nombreRol } from '../../lib/etiquetas'
import { formatoFecha } from './comun'

export function PasoInvitaciones({
  guardada,
  roles,
  disponibles,
  enviando,
  alReenviar,
}: {
  guardada: SesionDetalle
  roles: RolEjercicio[]
  disponibles: ParticipanteDisponible[]
  enviando: boolean
  alReenviar: () => void
}) {
  if (guardada.estado === 'borrador') {
    return (
      <section className="tarjeta">
        <h2>Invitaciones</h2>
        <p className="parrafo">
          Las invitaciones se envían por correo a cada participante cuando programas
          la sesión en el paso 5.
        </p>
      </section>
    )
  }

  const porEnviar = guardada.participantes.filter(
    (p) => p.invitacion === 'pendiente' || p.invitacion === 'fallida',
  ).length
  const aceptadas = guardada.participantes.filter((p) => p.invitacion === 'aceptada').length
  const persona = (id: string) => disponibles.find((u) => u.id === id)

  return (
    <>
      <section className="tarjeta">
        <div className="titulo-seccion">
          <div>
            <h2>Invitaciones</h2>
            <p className="texto-suave">
              {aceptadas} de {guardada.participantes.length} participantes confirmaron
              su asistencia.
            </p>
          </div>
          <button
            type="button"
            className="boton boton-primario"
            disabled={enviando || porEnviar === 0}
            onClick={alReenviar}
          >
            {porEnviar ? `Enviar ${porEnviar} pendiente(s)` : 'Todas enviadas'}
          </button>
        </div>
      </section>

      <section className="tarjeta tabla-contenedor">
        <table className="tabla">
          <thead>
            <tr>
              <th>Participante</th>
              <th>Rol</th>
              <th>Invitación</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            {guardada.participantes.map((p) => {
              const u = persona(p.usuario_id)
              return (
                <tr key={p.usuario_id}>
                  <td>
                    {u?.nombre ?? 'Usuario no disponible'}
                    {u && <div className="texto-suave">{u.correo}</div>}
                  </td>
                  <td>{nombreRol(roles, p.rol_codigo)}</td>
                  <td>
                    <InvitacionBadge estado={p.invitacion} />
                  </td>
                  <td className="texto-suave">
                    {p.invitacion === 'aceptada' &&
                      `Aceptó el ${formatoFecha(p.invitacion_aceptada_en)}`}
                    {p.invitacion === 'enviada' &&
                      `Enviada el ${formatoFecha(p.invitacion_enviada_en)}`}
                    {p.invitacion === 'fallida' && (
                      <span className="texto-peligro">{p.invitacion_error}</span>
                    )}
                    {p.invitacion === 'pendiente' && 'Todavía no se envió'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </section>
    </>
  )
}
